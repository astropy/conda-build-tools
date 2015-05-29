from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

from argparse import ArgumentParser
import os
import re
import hashlib
import tarfile

from binstar_client.scripts import cli
from binstar_client.errors import NotFound

from astropy.extern import six
from astropy.extern.six.moves import xmlrpc_client as xmlrpclib

from jinja2 import Environment, FileSystemLoader

from generate_initial_versions import get_pypi_info

BINSTAR_CHANNEL = 'astropy'
PYPI_XMLRPC = 'https://pypi.python.org/pypi'
BDIST_CONDA_FOLDER = 'bdist_conda'
TEMPLATE_FOLDER = 'recipe_templates'
RECIPE_FOLDER = 'recipes'


class Package(object):
    """
    A package to be built for conda.

    Parameters
    ----------

    pypi_name : str
        Name of the package on PyPI. Note that PyPI is not case sensitive.

    version: str, optional
        Version number of the package. ``None``, the default, implies the most
        recent version visible on PyPI should be used.
    """

    # The class should only need one client for communicating with PyPI
    client = xmlrpclib.ServerProxy(PYPI_XMLRPC)

    def __init__(self, pypi_name, version=None):
        self._pypi_name = pypi_name
        self.required_version = version
        self._build = False
        self._url = None
        self._md5 = None

    @property
    def pypi_name(self):
        """
        Name of the package on PyPI.
        """
        return self._pypi_name

    @property
    def conda_name(self):
        """
        Name of the package on binstar (conda), which requires lowercase
        names.
        """
        return self.pypi_name.lower()

    @property
    def required_version(self):
        """
        Version number of the package.
        """
        return self._required_version

    @required_version.setter
    def required_version(self, value):
        self._required_version = value.strip()

    @property
    def on_binstar(self):
        return self.on_binstar

    @property
    def build(self):
        """
        bool:
            ``True`` if this package needs to be built.
        """
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
        if not self._url:
            self._retrieve_package_metadata()

        return self._url

    @property
    def md5(self):
        if not self._md5:
            self._retrieve_package_metadata()

        return self._md5

    @property
    def filename(self):
        return self.url.split('/')[-1]

    def _retrieve_package_metadata(self):
        """
        Get URL and md5 checksum from PyPI for either the specified version
        or the most recent version.
        """
        if not self.required_version:
            version = get_pypi_info(self.pypi_name)
        else:
            version = self.required_version

        urls = self.client.release_urls(self.pypi_name, version)
        try:
            url = urls[0]['url']
            md5sum = urls[0]['md5_digest']
        except IndexError:
            # Apparently a pypi release isn't required to have any source?
            # If it doesn't, then return None
            print('No source found for {}: {}'.format(self.pypi_name,
                  self.required_version))
            url = None
            md5sum = None
        self._url = url
        self._md5 = md5sum

    def download(self, directory, checksum=True):
        """
        Download package and store in directory.

        Parameters
        ----------
        directory : str
            Directory in which to store the downloaded package.

        checksum: bool, optional
            If ``True``, check the MD5 checksum of the download.
        """
        loader = six.moves.urllib.request.URLopener()
        destination = os.path.join(directory, self.filename)
        print(destination)
        loader.retrieve(self.url, destination)
        if checksum:
            with open(destination, 'rb') as f:
                # Not worried about the packages being too big for memory.
                contents = f.read()
            md5_downloaded = hashlib.md5(contents).hexdigest()
            if md5_downloaded != self.md5:
                raise ValueError('checksum mismatch '
                                 'in {}'.format(self.filename))


def get_package_versions(requirements_path):
    """
    Read and parse list of packages.

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
        # Decide whether the package needs to be built by checking to see if
        # it exists on binstar.
        try:
            cli.main(args=['show', argument])
        except NotFound:
            package.build = True

    return [p for p in packages if p.build and not p.is_dev and p.url]


def main(args):
    packages = get_package_versions(args.requirements)
    to_build = construct_build_list(packages, conda_channel='astropy')
    needs_recipe = os.listdir(TEMPLATE_FOLDER)

    build_recipe = [p for p in to_build if p.conda_name in needs_recipe]
    build_bdist = [p for p in to_build if p.conda_name not in needs_recipe]

    if build_bdist:
        os.mkdir(BDIST_CONDA_FOLDER)

    if build_recipe:
        os.mkdir(RECIPE_FOLDER)
        full_template_path = os.path.abspath(TEMPLATE_FOLDER)
        jinja_env = Environment(loader=FileSystemLoader(full_template_path))

    for p in build_recipe:
        print('Building {} from recipe.'.format(p.conda_name))
        recipe_path = os.path.join(RECIPE_FOLDER, p.conda_name)
        template_path = os.path.join(TEMPLATE_FOLDER, p.conda_name)
        os.mkdir(recipe_path)
        templates = [d for d in os.listdir(template_path) if not d.startswith('.')]
        for template in templates:
            tpl = jinja_env.get_template('/'.join([p.conda_name, template]))
            rendered = tpl.render(version=p.required_version,
                                  md5=p.md5)
            with open(os.path.join(recipe_path, template), 'wt') as f:
                f.write(rendered)

    for p in build_bdist:
        p.download(BDIST_CONDA_FOLDER)
        source_archive = os.path.join(BDIST_CONDA_FOLDER, p.filename)
        source_destination = os.path.join(BDIST_CONDA_FOLDER,
                                          p.filename.rstrip('.tar.gz'))
        with tarfile.open(source_archive) as archive:
            archive.extractall(BDIST_CONDA_FOLDER)
        os.remove(source_archive)


if __name__ == '__main__':
    parser = ArgumentParser('command line tool for building packages.')
    parser.add_argument('requirements',
                        help='Full path to requirements.txt')
    args = parser.parse_args()
    main(args)
