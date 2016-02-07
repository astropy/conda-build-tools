from __future__ import print_function, division, absolute_import

from argparse import ArgumentParser


def main(args=None):
    if args is None:
        parser = ArgumentParser('Tool for generating skeleton package-'
                                'building directory.')
        parser.add_argument('--appveyor-secret', default='Fill me in',
                            help="Appveyor secret containing BINSTAR_TOKEN")
        parser.add_argument('--travis-secret', default='Fill me in',
                            help="Travis-CI secret containing BINSTAR_TOKEN")
        args = parser.parse_args()


if __name__ == '__main__':
    main()
