from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

from argparse import ArgumentParser
import os
import re
import xmlrpclib

from binstar_client.scripts import cli
from binstar_client.errors import NotFound

from astropy.extern import six

BINSTAR_CHANNEL = 'astropy'
PYPI_XMLRPC = 'https://pypi.python.org/pypi'


class Package(object):
    """docstring for Package"""
    def __init__(self, pypi_name, version=None):
        self._pypi_name = pypi_name
        self.required_version = version
        self._build = False
        self._url = None

    @property
    def pypi_name(self):
        return self._pypi_name

    @property
    def conda_name(self):
        return self.pypi_name.lower()

    @property
    def required_version(self):
        return self._required_version

    @required_version.setter
    def required_version(self, value):
        self._required_version = value.strip()

    @property
    def on_binstar(self):
        return self.on_binstar

    @property
    def build(self):
        return self._build

    @build.setter
    def build(self, value):
        # TODO: Make sure this is a bool
        self._build = value

    @property
    def is_dev(self):
        return not (re.search('[a-zA-Z]', self.required_version) is None)

    @property
    def url(self):
        if self._url:
            return self._url

        client = xmlrpclib.ServerProxy(PYPI_XMLRPC)
        urls = client.release_urls(self.pypi_name, self.required_version)
        try:
            return urls[0]['url']
        except IndexError:
            # Apparently a pypi release isn't required to have any source?
            # If it doesn't, then return None
            print('No source found for {}: {}'.format(self.pypi_name,
                  self.required_version))
            return None

    def download(self, directory):
        """
        Download package and store in directory.

        Parameters
        ----------
        directory : str
            Directory in which to store the downloaded package.
        """
        loader = six.moves.urllib.request.URLopener()
        destination = os.path.join(directory, self.url.split('/')[-1])
        print(destination)
        loader.retrieve(self.url, destination)


def get_package_version(requirements_path):
    """
    Read and parse list of packages, optionally normalizing by lower casing
    names.

    Parameters
    ----------

    requirements_path : str
        Path to ``requirements.txt``

    Returns
    -------

    list
        List of ``Package`` objects, one for each in the requirements file.
    """
    with open(requirements_path, 'rt') as f:
        # The requirements file is small, read it all in.
        package_list = f.readlines()

    packages = []
    for p in package_list:
        name, version = p.split('==')
        packages.append(Package(name, version=version))

    return packages


def construct_build_list(packages, conda_channel=None):
    channel = conda_channel or BINSTAR_CHANNEL
    argument_template = '{channel}/{package}/{version}'

    for package in packages:
        argument = argument_template.format(channel=channel,
                                            package=package.conda_name,
                                            version=package.required_version)
        print(argument)
        try:
            cli.main(args=['show', argument])
        except NotFound:
            package.build = True

    return [p for p in packages if p.build and not p.is_dev and p.url]


def main(args):
    print(os.getcwd())
    packages = get_package_version(args.requirements)
    to_build = construct_build_list(packages, conda_channel='astropy')
    for p in to_build:
        p.download('bdist_conda')
    #print('\n'.join([p.pypi_name for p in to_build]))
    #print('\n'.join([str(p.url) for p in to_build]))


if __name__ == '__main__':
    parser = ArgumentParser('command line tool for building packages.')
    parser.add_argument('requirements',
                        help='Full path to requirements.txt')
    args = parser.parse_args()
    main(args)
