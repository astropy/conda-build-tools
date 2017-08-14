from argparse import ArgumentParser
import os
from time import sleep

from warnings import warn
from ruamel import yaml
from github3 import login
from github3.exceptions import ForbiddenError
from git import Repo, GitCommandError


# Read in the yml file
# Loop over packages
#   Try forking to users account
#   Clone to remote directory
#   Set up remotes in that repo
def fork_and_clone(gh, packages, github_user, destination):
    for pdict in packages:
        package = pdict['name']
        print('Working on feedstock for: {}'.format(package))
        feedstock = package.lower() + '-feedstock'
        upstream_repo = gh.repository('conda-forge', feedstock)
        if not upstream_repo:
            warn('Feedstock repository not found for {}'.format(package))
            continue
        try:
            fork_repo = upstream_repo.create_fork()
        except ForbiddenError:
            # If the repo exists but is empty this is the error raised.
            # Skip further processing.
            warn('Feedstock {} exists on conda-forge but is '
                 'empty.'.format(feedstock))
            continue
        if not fork_repo:
            warn('Could not fork feedstock {}'.format(feedstock))
            continue
        else:
            print(('    Forked {} to {} (or fork '
                   'already existed)').format(feedstock, github_user))

        local_name = os.path.join(destination, feedstock)
        try:
            local_repo = Repo.clone_from(fork_repo.clone_url, local_name)
        except GitCommandError:
            warn('Destination clone for {} already exists'.format(feedstock))
            continue
        else:
            print('    Cloned {} to local directory {}'.format(feedstock,
                                                               destination))

        upstream_remote = local_repo.create_remote('upstream',
                                                   upstream_repo.clone_url)
        print('    Added remote upstream to local repository')
        upstream_remote.fetch()
        print('    Fetched from upstream remote')
        local_repo.heads.master.set_tracking_branch(
            upstream_remote.refs.master)
        print('    Set tracking branch on master to the upstream remote')
        upstream_remote.pull()
        print('    Pulled in changes from upstream master')
        # Sleep briefly between repos...
        sleep(0.5)


def main(arguments=None):
    parser = ArgumentParser('Script to fork/clone a bunch of feedstocks.')
    parser.add_argument('packages_yaml',
                        help=('Packages to copy, as a yaml dictionary. '
                              'Keys are package names, values are version, '
                              'or None for the latest version from '
                              'the source.'))
    parser.add_argument('--destination-dir', default='.',
                        help=('Local directory into which feedstock should '
                              'be cloned.'))
    parser.add_argument('--github-user', '-g', default='mwcraig',
                        help=('Github user name of the account to which '
                              'feedstocks should be forked.'))
    parser.add_argument('--token', default='',
                        help=('github API token. May set '
                              'environmental variable GITHUB_TOKEN '
                              'instead.'))

    if arguments is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(arguments)

    github_user = args.github_user
    destination = args.destination_dir

    token = args.token
    # No token on command line, try the environment...
    if not token:
        token = os.getenv('GITHUB_TOKEN')

    # Still no token, so raise an error
    if not token:
        raise RuntimeError('Set a github API token before running')

    # Set up github and read the packages before we get started.
    gh = login(token=token)

    # Check that the logged-in name matches the command-line name
    if gh.me().login != github_user:
        raise RuntimeError('Username {} from github does not match '
                           'the username {} on the command '
                           'line'.format(gh.me().login, github_user))

    with open(args.packages_yaml) as f:
        packages = yaml.safe_load(f)

    fork_and_clone(gh, packages, github_user, destination)


if __name__ == '__main__':
    main()
