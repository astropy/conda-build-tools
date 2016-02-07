Purpose
=======

This builder-bot makes `conda`_ packages for `astropy`_ affiliated packages.

Design decisions
================

+ `conda`_ packages will be made only for non-dev versions of affiliated
  packages.
+ A dev version is any version whose name contains letters (this is broader
  than `PEP 440`_ but avoids the need for any intelligent parsing).
+ `conda`_ recipes are avoided wherever possible to avoid duplicating
  information already in the ``setup.py`` of most affiliated packages.
+ Where possible, python scripts are used to do the work to avoid separate
  Linux/Mac and Windows scripts.

Maintaining the bot
===================

Update version of existing package
----------------------------------

Open a pull request that updates the version number of the package(s) to be
built. Doing so will trigger builds of the new package(s) on all platforms.
Packages are automatically upload to the `astropy binstar channel`_.

Add a new affiliated package
----------------------------

1. Figure out how to build the `conda`_ package.
    + First try ``python setup.py bdist_conda``.
    + If that fails, try to convince the package maintainer to update
      their ``setup.py`` so that this works.
    + If that fails, try ``conda skeleton pypi packagename`` to generate
      the initial recipe and modify as needed until
      ``conda build packagename`` works.
2. If ``python setup.py bdist_conda`` works you only need to open a pull
   request on this repo that adds the package and version to
   ``requirements.txt``.
3. If the package needs a recipe to build you need to open a pull request that:
    + Adds the package information to ``requirements.txt``
    + Adds a template recipe for the package to ``recipe-templates``.

License
=======

This software is licensed under a BSD 3-clause license. See ``LICENSE.rst`` for details.

.. _astropy: http://astropy.org
.. _conda: http://conda.pydata.org/
.. _PEP 440: https://www.python.org/dev/peps/pep-0440/
.. _astropy binstar channel: http://binstar.org/astropy
