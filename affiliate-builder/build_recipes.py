from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

from obvci.conda_tools.build_directory import Builder
from prepare_packages import RECIPE_FOLDER, BINSTAR_CHANNEL


def main(recipe_dir=RECIPE_FOLDER):
    builder = Builder(recipe_dir, BINSTAR_CHANNEL, 'main')
    builder.main()
    print('moo')


if __name__ == '__main__':
    main()
