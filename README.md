# extruder

This is a pair of scripts to create and manage a set of packages to be built
with [`conda build`](https://github.com/conda/conda-build).

The hard work is really done by `conda build` and
[Obvious-CI](https://github.com/pelson/Obvious-CI)
(soon to be replaced by [conda-build-all](https://github.com/SciTools/conda-build-all))

# Installation


## conda package

Note there are a couple non-default channels you need to include to pick up
the dependencies for extruder:

```
conda install -c astropy -c conda-forge extruder
```

## from source

Clone the repository, then:

```
python setup.py install
```

# Usage

This package builds conda packages for a set of python packages using the
continuous integration services Travis (for Linux and Mac) and Appveyor (for
Windows).

For each package listed in `requirements.yml` a conda recipe is constructed.
If a recipe template is present, that is used generate the recipe, otherwise
`conda skeleton` is used to construct a recipe.

The expectation is that you will have a folder laid out like this:

```
your_folder_to_build/
    requirements.yml     # required, lists packages to be built.
    recipe_templates/    # optional, for packages conda skeleton would fail on.
        recipe-template-for-one-package/
        ....
    .travis.yml          # Not required to run extruder scripts, but...
    appveyor.yml         # ...you presumably want these to build on CI services.
```


The packages to be built should be listed in a file called `requirements.yml`;
a [sample one](extruder/data/template-build-files/requirements.yml) is
included in this repository. In addition to package name and version it can
contain restrictions on the building of conda packages, and options that need
to be passed to `setup.py` for `conda skeleton` to succeed. See the sample for
a list of settings.

If there is a recipe template for a particular package that is used to
construct the recipe; a template is useful when the recipe constructed by
`conda skeleton` would fail. The recipe template should follow the usual rules
for conda recipes; the values of the version, and the download link in the
recipe from PyPI, will automatically be filled in from `requirements.yml`. A
[sample recipe template](extruder/data/template-build-files/recipe_templates)
is included in this repository.

## Starting a new collection to make conda packages for

The easiest way to get started is to allow this package to create a skeleton for you:

```
$ extrude_skeleton
```

This creates the files you need to get started (i.e. those listed at the
beginning of this section).

## Making the recipes

Assuming you have followed the naming conventions for the files at the
beginning of this section, all it takes to generate the recipes is

```
$ extrude_recipes requirements.yml
```

This creates a folder called `recipes` that contains a recipe for each package
in `requirements.yml`.

# License

This software is licensed under a BSD 3-clause license. See ``LICENSE.rst`` for details.

.. _astropy: http://astropy.org
.. _conda: http://conda.pydata.org/
.. _PEP 440: https://www.python.org/dev/peps/pep-0440/
.. _astropy binstar channel: http://binstar.org/astropy
