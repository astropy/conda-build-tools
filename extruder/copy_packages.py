from __future__ import print_function

from argparse import ArgumentParser
import os

from ruamel import yaml

from binstar_client.utils import get_server_api
from binstar_client.errors import NotFound

from conda.version import VersionOrder

__all__ = ['PackageCopier']


class PackageCopier(object):
    def __init__(self, source, destination, input_packages, token=''):
        """
        Parameters
        ----------

        source : ``str``
            Name of source conda channel.
        destination : ``str``
            Name of destination conda channel.
        input_package : ``dict``
            Dictionary in which keys are package names and values are either
            a string version number (e.g. ``'1.0.1'``) or ``None``, which
            indicates the latest version on the source channel should be
            copied. This dictionary should contain the packages that
            potentially need to be copied.
        token : ``str``, optional
            Token for conda API. Needed for the actual copy operation.
        """
        self.source = source
        self.destination = destination
        self.input_packages = input_packages
        self.api = get_server_api(token)
        self.to_copy = self._package_versions_to_copy()

    def _package_versions_to_copy(self):
        """
        Determine which version of each package in packages
        should be copied from conda channel source to channel
        destination.

        Returns
        -------
        ``dict``
            Dictionary whose keys are the packages that actually need to be
            copied and whose values are the version to be copied.
        """
        packages = self.input_packages

        copy_versions = {}
        for p, version in packages.items():
            copy_builds = []
            need_to_copy = False
            # This will end up True if  the version exists on both src and dest
            # and triggers a comparison of file names. Technically, it could
            # be omitted, but seems more likely to be clear to future me.
            check_builds = False
            cf = self.api.package(self.source, p)
            cf_version = VersionOrder(cf['latest_version'])

            if version is not None:
                pinned_version = VersionOrder(version)
            else:
                pinned_version = None

            if pinned_version is not None:
                if str(pinned_version) not in cf['versions']:
                    error_message = ('Version {} of package {} not '
                                     'found on source channel {}.')
                    err = error_message.format(pinned_version, p,
                                               self.source)
                    raise RuntimeError(err)

            try:
                ap = self.api.package(self.destination, p)
            except NotFound:
                need_to_copy = True
                ap_version = None
            else:
                ap_version = VersionOrder(ap['latest_version'])
                if pinned_version is None:
                    if cf_version > ap_version:
                        need_to_copy = True
                    elif cf_version == ap_version:
                        check_builds = True

                else:
                    if str(pinned_version) not in ap['versions']:
                        need_to_copy = True
                    else:
                        check_builds = True
                if check_builds:
                    # If we get here it means that the same version is on both
                    # source and destination so we need to check the individual
                    # builds.
                    copy_builds = \
                        self._check_for_missing_builds(cf,
                                                       ap,
                                                       cf_version)
                    need_to_copy = len(copy_builds) > 0
            if need_to_copy:
                copy_versions[p] = (str(cf_version), copy_builds)

        return copy_versions

    def _check_for_missing_builds(self, source, dest, version):
        """
        For two packages that have the same version, see if there are any
        files on the source that are not on the destination.

        source and dest are both conda channels, and version
        should be a string.
        """
        def files_for_version(channel, version):
            files = [f['basename'] for f in channel['files']
                     if VersionOrder(version) == VersionOrder(f['version'])]
            return files

        source_files = files_for_version(source, version)
        destination_files = files_for_version(dest, version)

        need_to_copy = [src for src in source_files
                        if src not in destination_files]

        return need_to_copy

    def copy_packages(self):
        """
        Actually do the copying of the packages.
        """
        for p, v in self.to_copy.items():
            version, buildnames = v
            if not buildnames:
                # Copy all of the builds for this version
                self.api.copy(self.source, p, v, to_owner=self.destination)
            else:
                for build in buildnames:
                    self.api.copy(self.source, p, version,
                                  basename=build,
                                  to_owner=self.destination)


def main(arguments=None):
    parser = ArgumentParser('Simple script for copying packages '
                            'from one conda owner to another')
    parser.add_argument('packages_yaml',
                        help=('Packages to copy, as a yaml dictionary. '
                              'Keys are package names, values are version, '
                              'or None for the latest version from '
                              'the source.'))
    parser.add_argument('--source', default='conda-forge',
                        help='Source conda channel owner.')
    parser.add_argument('--token', default='',
                        help=('anaconda.org API token. May set '
                              'environmental variable BINSTAR_TOKEN '
                              'instead.'))
    parser.add_argument('destination_channel',
                        help=('Destination conda channel owner.'))
    if arguments is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(arguments)

    source = args.source
    dest = args.destination_channel
    package_file = args.packages_yaml
    token = args.token

    with open(package_file) as f:
        packages = yaml.load(f)

    # No token on command line, try the environment...
    if not token:
        token = os.getenv('BINSTAR_TOKEN')

    # Still no token, so raise an error
    if not token:
        raise RuntimeError('Set an anaconda.org API token before running')

    pc = PackageCopier(source, dest, packages, token=token)
    pc.copy_packages()


if __name__ == '__main__':
    main()
