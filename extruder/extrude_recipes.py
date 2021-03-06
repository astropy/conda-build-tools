from __future__ import (division, print_function, absolute_import)


from argparse import ArgumentParser
import os
import re

from ruamel import yaml

from conda import config
from conda_build.api import skeletonize
from binstar_client.utils import get_server_api
from binstar_client.errors import NotFound

from six.moves import xmlrpc_client as xmlrpclib

from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound

PYPI_XMLRPC = 'https://pypi.python.org/pypi'
TEMPLATE_FOLDER = 'recipe_templates'
RECIPE_FOLDER = 'recipes'
ALL_PLATFORMS = ['osx-64', 'linux-64', 'linux-32', 'win-32', 'win-64']

CONDA_FORGE_FEEDSTOCK_TARBALL = ('https://github.com/conda-forge/{}-feedstock'
                                 '/archive/master.tar.gz')


def get_pypi_info(name):
    client = xmlrpclib.ServerProxy(PYPI_XMLRPC, allow_none=True)
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
    client = xmlrpclib.ServerProxy(PYPI_XMLRPC, allow_none=True)

    def __init__(self, pypi_name, version=None,
                 numpy_compiled_extensions=False,
                 setup_options=None,
                 python_requirements=None,
                 numpy_requirements=None,
                 excluded_platforms=None,
                 include_extras=False):
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
        self._numpy_requirements = numpy_requirements
        self._excluded_platforms = excluded_platforms or []
        self._include_extras = include_extras

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
        if value is not None:
            self._required_version = str(value).strip()
        else:
            self._required_version = value

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
    def numpy_requirements(self):
        return self._numpy_requirements

    @property
    def include_extras(self):
        return self._include_extras

    @property
    def is_dev(self):
        # Be more explicit about dev and pre-release versions
        return not (re.search('a|b|rc|dev', self.required_version) is None)

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

        Also excludes any platforms indicated in requirements.yml,
        """
        # Lazy memoization...
        if self._build_platforms:
            return self._build_platforms

        platform_info = self.extra_meta

        try:
            platforms = platform_info['extra']['platforms']
        except KeyError:
            platforms = ALL_PLATFORMS

        platforms = list(set(platforms) - set(self._excluded_platforms))

        self._build_platforms = platforms
        return self._build_platforms

    @property
    def build_pythons(self):
        if self._build_pythons:
            return self._build_pythons
        try:
            pythons = self.extra_meta['extra']['pythons']
        except KeyError:
            pythons = ["27", "35"]

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
        numpy_requirements = p.get('numpy_build_restrictions', [])
        version = p.get('version', None)
        excluded_platforms = p.get('excluded_platforms', [])
        include_extras = p.get('include_extras', False)

        # TODO: Get supported platforms from requirements,
        #       not from recipe template.
        packages.append(Package(p['name'],
                                version=version,
                                setup_options=helpers,
                                numpy_compiled_extensions=numpy_extensions,
                                python_requirements=python_requirements,
                                numpy_requirements=numpy_requirements,
                                excluded_platforms=excluded_platforms,
                                include_extras=include_extras))

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

    additional_arguments = ['--version', str(package.required_version),
                            '--output-dir', path]
    additional_arguments = {}
    if package.include_extras:
        additional_arguments['all_extras'] = True

    # Options below ensure an egg is not included in the built package
    additional_arguments['setup_options'] = [
        '--single-version-externally-managed',
        '--record rec.txt'
    ]

    if package.setup_options:
        additional_arguments['setup_options'].append(package.setup_options)

    if package.numpy_compiled_extensions:
        additional_arguments['pin_numpy'] = True

    skeletonize(package.pypi_name, 'pypi',
                output_dir=path,
                version=str(package.required_version),
                **additional_arguments)


def get_conda_forge_version(package):
    """
    Check whether we can copy version we want from conda-forge.
    """
    api = get_server_api('')

    # A NotFound error will be raised if the package is not found.
    conda_forge = api.package('conda-forge', package.conda_name)

    if package.required_version:
        return package.required_version in conda_forge["versions"]
    else:
        # No version was specified, so assume the latest is good enough.
        return True


def inject_requirements(package, recipe_path):
    """
    Two packages get special treatment so that restrictions on build versions,
    which may be more restrictive than the requirements of the package itself.

    Those two packages are python and numpy.
    """
    meta_path = os.path.join(recipe_path, 'meta.yaml')
    with open(meta_path) as f:
        recipe = yaml.load(f, yaml.RoundTripLoader)

    spec = []
    if package.python_requirements:
        spec.append(' '.join(['python', package.python_requirements]))
    if package.numpy_requirements:
        spec.append(' '.join(['numpy', package.numpy_requirements]))

    if spec:
        for section in ['build', 'run']:
            recipe['requirements'][section].extend(spec)

    with open(meta_path, 'w') as f:
        yaml.dump(recipe, f, Dumper=yaml.RoundTripDumper,
                  default_flow_style=False)


def main(args=None):
    """
    Generate recipes for packages either from recipe templates, by copying
    from conda-forge, or by using conda skeleton.
    """
    if args is None:
        parser = ArgumentParser('command line tool for building packages.')
        parser.add_argument('requirements',
                            help='Path to requirements.yml')
        parser.add_argument('--template-dir', default=TEMPLATE_FOLDER,
                            help="Path the folder of recipe templates, if "
                                 "any. Default: '{}'".format(TEMPLATE_FOLDER))
        parser.add_argument('--dont-copy-conda-forge', action='store_true',
                            default=False, dest='dont_copy_conda_forge',
                            help="Do not copy packages from conda-forge. "
                                 "Default is False.")
        args = parser.parse_args()
        template_dir = args.template_dir
        dont_copy_conda_forge = args.dont_copy_conda_forge

    packages = get_package_versions(args.requirements)

    packages = [p for p in packages if p.supported_platform]

    try:
        needs_recipe = os.listdir(template_dir)
    except OSError:
        needs_recipe = []

    build_recipe = [p for p in packages if p.conda_name in needs_recipe]
    build_not_recipe = [p for p in packages if p.conda_name not in needs_recipe]

    if build_recipe or build_not_recipe:
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
        inject_requirements(p, recipe_path)

    # check conda-forge for a recipe, and if it is not found, add to the skeleton
    # list.
    build_skeleton = []
    copy_from_conda_forge = {}
    for p in build_not_recipe:
        # Try grabbing the recipe from conda-forge
        try:
            if dont_copy_conda_forge:
                in_conda_forge = False
            else:
                in_conda_forge = get_conda_forge_version(p)
        except NotFound:
            build_skeleton.append(p)
            continue
        else:
            if not in_conda_forge:
                build_skeleton.append(p)
                continue

        copy_from_conda_forge[p.conda_name] = p.required_version
        print("Will copy {} directly from the "
              "conda-forge channel".format(p.conda_name))

    if copy_from_conda_forge:
        with open('copy_from.yaml', 'w') as f:
            yaml.dump(copy_from_conda_forge, f)

    # Use conda skeleton to generate recipes for the simple cases
    for p in build_skeleton:
        print('generating skeleton for {}'.format(p.conda_name))
        recipe_destination = os.path.join(RECIPE_FOLDER, p.conda_name)
        generate_skeleton(p, RECIPE_FOLDER)

        inject_requirements(p, recipe_destination)


if __name__ == '__main__':
    main()
