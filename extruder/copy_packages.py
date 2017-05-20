from __future__ import print_function

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
        package : ``dict``
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
            need_to_copy = False

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
                else:
                    if str(pinned_version) not in ap['versions']:
                        need_to_copy = True
            if need_to_copy:
                copy_versions[p] = str(cf_version)

        return copy_versions

    def copy_packages(self):
        """
        Actually do the copying of the packages.
        """
        print(self.api.token)
        for p, v in self.to_copy.items():
            self.api.copy(self.source, p, v, to_owner=self.destination)
