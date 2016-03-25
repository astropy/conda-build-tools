from __future__ import (division, print_function, absolute_import)


from argparse import ArgumentParser
import os
import re
import subprocess
from collections import OrderedDict

import yaml

from conda import config

from six.moves import xmlrpc_client as xmlrpclib

from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound

PYPI_XMLRPC = 'https://pypi.python.org/pypi'
TEMPLATE_FOLDER = 'recipe_templates'
RECIPE_FOLDER = 'recipes'
ALL_PLATFORMS = ['osx-64', 'linux-64', 'linux-32', 'win-32', 'win-64']


def setup_yaml():
    """
    Enable yaml to serialize an OrderedDict as a mapping.

    Cut and paste directly from: http://stackoverflow.com/a/31605131

    It in turn was condensed version of: http://stackoverflow.com/a/8661021
    """
    represent_dict_order = lambda self, data:  \
        self.represent_mapping('tag:yaml.org,2002:map', data.items())
    yaml.add_representer(OrderedDict, represent_dict_order)


def get_pypi_info(name):
    client = xmlrpclib.ServerProxy(PYPI_XMLRPC)
    pypi_stable = client.package_releases(name)
    try:
        return pypi_stable[0]
    except IndexError:
        return None


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

    def __init__(self, pypi_name, version=None,
                 numpy_compiled_extensions=False,
                 setup_options=None,
                 python_requirements=None):
        self._pypi_name = pypi_name
        self.required_version = version
        self._build = False
        self._url = None
        self._md5 = None
        self._build_platforms = None
        self._extra_meta = None
        self._build_pythons = None
        self._numpy_compiled_extensions = numpy_compiled_extensions
        self._setup_options = setup_options
        self._python_requirements = python_requirements

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
        self._required_version = str(value).strip()

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
    def numpy_compiled_extensions(self):
        return self._numpy_compiled_extensions

    @property
    def setup_options(self):
        return self._setup_options

    @property
    def python_requirements(self):
        return self._python_requirements

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

    @property
    def build_platforms(self):
        """
        Return list of platforms on which this package can be built.

        Defaults to the value of ``ALL_PLATFORMS``.

        Checks for build information by looking at recipe *templates*, which
        is probably not really the way to go...might be more generalizable if
        it looked at recipes instead.
        """
        # Lazy memoization...
        if self._build_platforms:
            return self._build_platforms

        platform_info = self.extra_meta

        try:
            platforms = platform_info['extra']['platforms']
        except KeyError:
            platforms = ALL_PLATFORMS

        self._build_platforms = platforms
        return self._build_platforms

    @property
    def build_pythons(self):
        if self._build_pythons:
            return self._build_pythons
        try:
            pythons = self.extra_meta['extra']['pythons']
        except KeyError:
            pythons = ["27", "34"]

        # Make sure version is always a string so it can be compared
        # to CONDA_PY later.
        self._build_pythons = [str(p) for p in pythons]
        return self._build_pythons

    @property
    def extra_meta(self):
        """
        The 'extra' metadata, for now read in from meta.yaml.
        """
        if self._extra_meta is not None:
            return self._extra_meta

        try:
            meta = render_template(self, 'meta.yaml')
        except TemplateNotFound:
            # No recipe, make an empty meta for now.
            meta = ''

        platform_info = yaml.safe_load(meta) if meta else {}
        self._extra_meta = platform_info

        return self._extra_meta

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
            # Many packages now have wheels, need to iterate over download
            # URLs to get the source distribution.
            for a_url in urls:
                if a_url['packagetype'] == 'sdist':
                    url = a_url['url']
                    md5sum = a_url['md5_digest']
                    break
            else:
                # No source distribution, so raise an index error
                raise IndexError
        except IndexError:
            # Apparently a pypi release isn't required to have any source?
            # If it doesn't, then return None
            print('No source found for {}: {}'.format(self.pypi_name,
                  self.required_version))
            url = None
            md5sum = None
        self._url = url
        self._md5 = md5sum

    @property
    def supported_platform(self):
        """
        True if the current build platform is supported by the package, False
        otherwise.
        """
        return config.subdir in self.build_platforms


def get_package_versions(requirements_path):
    """
    Read and parse list of packages.

    Parameters
    ----------

    requirements_path : str
        Path to ``requirements.yml``

    Returns
    -------

    list
        List of ``Package`` objects, one for each in the requirements file.
    """
    with open(requirements_path, 'rt') as f:
        package_list = yaml.safe_load(f)

    packages = []
    for p in package_list:
        helpers = p.get('setup_options', None)
        numpy_extensions = p.get('numpy_compiled_extensions', False)
        python_requirements = p.get('python', [])
        version = p.get('version', None)
        # TODO: Get supported platforms from requirements,
        #       not from recipe template.
        packages.append(Package(p['name'],
                                version=version,
                                setup_options=helpers,
                                numpy_compiled_extensions=numpy_extensions,
                                python_requirements=python_requirements))

    return packages


def render_template(package, template, folder=TEMPLATE_FOLDER):
    """
    Render recipe components from jinja2 templates.

    Parameters
    ----------

    package : Package
        :class:`Package` object for which template will be rendered.
    template : str
        Name of template file, path relative to ``folder``.
    folder : str
        Path to folder containing template.
    """
    full_template_path = os.path.abspath(folder)
    jinja_env = Environment(loader=FileSystemLoader(full_template_path))
    tpl = jinja_env.get_template('/'.join([package.conda_name, template]))
    rendered = tpl.render(version=package.required_version, md5=package.md5)
    return rendered


def generate_skeleton(package, path):
    """
    Use conda skeleton pypi to generate a recipe for a package and
    save it to path.

    Parameters
    ----------

    package: Package
        The package for which a recipe is to be generated.

    path: str
        Path to which the recipe should be written.
    """

    additional_arguments = ['--all-extras',
                            '--version', str(package.required_version),
                            '--output-dir', path]

    if package.setup_options:
        additional_arguments.extend(['--setup-options={}'.format(package.setup_options)])

    if package.numpy_compiled_extensions:
        additional_arguments.append('--pin-numpy')

    subprocess.check_call(["conda", "skeleton", "pypi", package.pypi_name] +
                          additional_arguments)


def inject_python_requirements(package, recipe_path):
    meta_path = os.path.join(recipe_path, 'meta.yaml')
    with open(meta_path) as f:
        recipe = yaml.safe_load(f)
    python_spec = ' '.join(['python', package.python_requirements])
    for section in ['build', 'run']:
        recipe['requirements'][section].append(python_spec)

    with open(meta_path, 'w') as f:
        yaml.dump(recipe, f, default_flow_style=False)


def main(args=None):
    """
    Generate recipes for packages either from recipe templates or by using
    conda skeleton.
    """
    if args is None:
        parser = ArgumentParser('command line tool for building packages.')
        parser.add_argument('requirements',
                            help='Path to requirements.yml')
        parser.add_argument('--template-dir', default=TEMPLATE_FOLDER,
                            help="Path the folder of recipe templates, if "
                                 "any. Default: '{}'".format(TEMPLATE_FOLDER))
        args = parser.parse_args()
        template_dir = args.template_dir

    packages = get_package_versions(args.requirements)

    packages = [p for p in packages if p.supported_platform]

    try:
        needs_recipe = os.listdir(template_dir)
    except OSError:
        needs_recipe = []

    build_recipe = [p for p in packages if p.conda_name in needs_recipe]
    build_skeleton = [p for p in packages if p.conda_name not in needs_recipe]

    if build_recipe or build_skeleton:
        os.mkdir(RECIPE_FOLDER)

    # Write recipes from templates.
    for p in build_recipe:
        print('Writing recipe for {}.'.format(p.conda_name))
        recipe_path = os.path.join(RECIPE_FOLDER, p.conda_name)
        template_path = os.path.join(template_dir, p.conda_name)
        os.mkdir(recipe_path)
        templates = [d for d in os.listdir(template_path) if
                     not d.startswith('.')]
        for template in templates:
            rendered = render_template(p, template, folder=template_dir)
            with open(os.path.join(recipe_path, template), 'wt') as f:
                f.write(rendered)

    # Use conda skeleton to generate recipes for the simple cases
    for p in build_skeleton:
        recipe_destination = os.path.join(RECIPE_FOLDER, p.conda_name)
        generate_skeleton(p, RECIPE_FOLDER)
        if p.python_requirements:
            inject_python_requirements(p, recipe_destination)


if __name__ == '__main__':
    main()
