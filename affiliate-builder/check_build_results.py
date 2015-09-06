from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os

import conda_build.config as config
from prepare_packages import RECIPE_FOLDER, BINSTAR_CHANNEL, BDIST_CONDA_FOLDER


def package_in_list(package_name, package_list):
    """
    Iterate through list of packages, returning True if the package is in
    the list and False otherwise.

    Parameters
    ----------

    package_name : str
        Name of package.
    package_list : list
        List of package names.

    Returns
    -------

    bool
        ``True`` if there is a package in the list whose name starts with
        ``package_name``, ``False`` otherwise.
    """
    for p in package_list:
        if p.startswith(package_name):
            return True
    else:
        return False


def main(recipe_dir, bdist_conda_dir):
    """
    Check, for each package that was to have been built, whether the
    package was actually built.

    The check is fairly simple: every package in
    the recipe or bdist_conda directory should have a corresponding conda
    package. If it doesn't, declare failure and move on.

    Parameters
    ----------

    recipe_dir : str
        Directory which, if it exists, has a subdirectory for each package to
        be built with ``conda build``.
    bdist_conda_dir : str
        Directory which, if it exists, has a subdirectory for each package to
        be built with ``setup.py bdist_conda``
    """
    built_packages = os.listdir(config.config.bldpkgs_dir)

    try:
        recipes = os.listdir(recipe_dir)
    except OSError:
        recipes = []

    try:
        bdist_conda = os.listdir(bdist_conda_dir)
    except OSError:
        bdist_conda = []

    expected_packages = recipes + bdist_conda

    not_built = [package for package in expected_packages
                 if not package_in_list(package, built_packages)]

    if not_built:
        raise RuntimeError("The following packages were not built:\n"
                           "{}".format('\n'.join(not_built)))


if __name__ == '__main__':
    main(RECIPE_FOLDER, BDIST_CONDA_FOLDER)
