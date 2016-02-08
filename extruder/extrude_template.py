from __future__ import print_function, division, absolute_import

from argparse import ArgumentParser
import os
import shutil

from jinja2 import Environment, FileSystemLoader


def main(args=None):
    """
    Copy all of the files needed from the source distribution to the current
    directory.
    """

    if args is None:
        parser = ArgumentParser('Tool for generating skeleton package-'
                                'building directory. All files created in the '
                                'current directory.')
        parser.add_argument('--appveyor-secret', default='Fill me in',
                            help="Appveyor secret containing BINSTAR_TOKEN")
        parser.add_argument('--travis-secret', default='Fill me in',
                            help="Travis-CI secret containing BINSTAR_TOKEN")
        args = parser.parse_args()

        skeleton_base_path = os.path.dirname(os.path.abspath(__file__))

        skeleton_file_dir = os.path.join(skeleton_base_path,
                                         'data',
                                         'template-build-files')

        for ci_file in ['.travis.yml', 'appveyor.yml']:
            jinja_env = Environment(loader=FileSystemLoader(skeleton_file_dir))
            tpl = jinja_env.get_template(ci_file)
            rendered = tpl.render(appveyor_binstar_token=args.appveyor_secret,
                                  travis_binstar_token=args.travis_secret)
            with open(ci_file, 'w') as f:
                f.write(rendered)

        shutil.copy(os.path.join(skeleton_file_dir, 'requirements.yml'), '.')
        template_folder = 'recipe-templates'
        shutil.copytree(os.path.join(skeleton_file_dir, template_folder),
                        template_folder)


if __name__ == '__main__':
    main()
