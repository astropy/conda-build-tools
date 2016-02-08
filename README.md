# extruder

This is a pair of scripts to create and manage a set of packages to be built
with `[conda build](https://github.com/conda/conda-build)`.

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

The packages to be built should be listed in a file called `requirements.yml`;
a [sample one](extruder/data/template-build-files/requirements.yml) is
included in this repository.

# License

This software is licensed under a BSD 3-clause license. See ``LICENSE.rst`` for details.

.. _astropy: http://astropy.org
.. _conda: http://conda.pydata.org/
.. _PEP 440: https://www.python.org/dev/peps/pep-0440/
.. _astropy binstar channel: http://binstar.org/astropy
