from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os
import glob

from conda import config
#from conda_build.metadata import MetaData

from binstar_client.inspect_package.conda import inspect_conda_package

from obvci.conda_tools.build import upload
from obvci.conda_tools.build_directory import Builder

from prepare_packages import RECIPE_FOLDER, BINSTAR_CHANNEL, BDIST_CONDA_FOLDER


def main():
    # Get our binstar client from the Builder to get BINSTAR_TOKEN obfuscation
    # in windows builds.
    builder = Builder(RECIPE_FOLDER, BINSTAR_CHANNEL, 'main')
    bdists = os.listdir(BDIST_CONDA_FOLDER)
    conda_builds_dir = os.path.join(config.default_prefix,
                                    'conda-bld', config.subdir)
    built_packages = glob.glob(os.path.join(conda_builds_dir, '*.tar.bz2'))
    for package in built_packages:
        _, package_file = os.path.split(package)
        name = package_file.split('-')[0]

        if name in bdists:
            # Need to upload this one...
            # First grab the metadata from the package, which requires
            # opening the file.

            # SKIP THIS VESTIGAL CRAP
            # with open(package) as f:
            #     package_data, release, file_data = inspect_conda_package(package, f)

            # print(package_data, release, file_data)
            # #package_data.update({'version': release['version']})
            # package_data.update(release)
            # package_data.update({'build': {'string': file_data['attrs']['build']}})
            # package_data.update(file_data)
            # meta = MetaData.fromdict({'package': package_data})
            # meta.check_fields()
            # print(meta)
            # print('DIST:', meta.dist())

            # RESUME READING HERE
            # Not going to lie: after fighting with conda for 90 minutes to
            # construct a proper MetaData object from a built package, I give
            # up.

            # Instead, create an object with one method, dist, which returns
            # the build string and be done with it.
            class MetaData(object):
                def __init__(self, dist_info):
                    self._dist_info = dist_info

                def dist(self):
                    return self._dist_info

            meta = MetaData(package_file.split('.tar.bz2')[0])
            # Upload it

            upload(builder.binstar_cli, meta, BINSTAR_CHANNEL)


if __name__ == '__main__':
    main()
