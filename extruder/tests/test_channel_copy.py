import pytest

from os import getenv

from binstar_client.utils import get_server_api
from binstar_client.errors import NotFound

from ..copy_packages import PackageCopier

SOURCE = 'conda-forge'

DEST = 'astropy-channel-copy-test'
# Destination channel contains only the packages:

# wcsaxes
#   only versions 0.7 and 0.8, but not the latest on conda-forge,
#   which is 0.9.
# sep
#   only version 0.5.2, copied from channel mwcraig,
#   which contains only that version.


def test_package_not_on_source():
    # Package does not exist on source channel
    # Expected outcome: NotFound
    packages = {'asudifjqeiroufnver': None}
    with pytest.raises(NotFound):
        PackageCopier(SOURCE, DEST, packages)


# Whether or not version exists on destination channel:

def test_version_not_in_source():
    # Package version is pinned and...
    # ...pinned version is not in source channel
    #    Expected outcome: RuntimeError and specific message
    packages = {'wcsaxes': '0.0.0'}
    with pytest.raises(RuntimeError):
        PackageCopier(SOURCE, DEST, packages)


# Package version is pinned and...
def test_version_pinned_not_in_destination():
    # ...pinned version is not in destination channel
    #    Expected outcome: copy
    packages = {'wcsaxes': '0.9'}
    pc = PackageCopier(SOURCE, DEST, packages)
    assert 'wcsaxes' in pc.to_copy


def test_version_pinned_in_destination():
    # ...pinned version is in destination channel
    #    Expected outcome: No copy
    packages = {'wcsaxes': '0.8'}
    pc = PackageCopier(SOURCE, DEST, packages)
    assert 'wcsaxes' not in pc.to_copy


# Package version is not pinned and...
def test_version_not_pinned_not_in_destination():
    # ...destination channel is not up to date
    #    Expected outcome: copy
    packages = {'wcsaxes': None}
    pc = PackageCopier(SOURCE, DEST, packages)
    assert 'wcsaxes' in pc.to_copy


def test_version_not_pinned_no_update_needed():
    # ...destination is up to date
    #    Expected outcome: no copy
    packages = {'sep': None}
    pc = PackageCopier('mwcraig', DEST, packages)
    assert 'sep' not in pc.to_copy


token = getenv('COPY_TEST_BINSTAR_TOKEN')


@pytest.mark.skipif(token is None,
                    reason='binstar token not set')
def test_package_copying():
    api = get_server_api(token)
    packages = {'wcsaxes': None}
    pc = PackageCopier(SOURCE, DEST, packages, token=token)

    # Make sure v0.9 has not accidentally ended up in the channel.
    dest_wcs = api.package(DEST, 'wcsaxes')
    assert "0.9" not in dest_wcs['versions']

    # Copy 0.9 to the channel.
    pc.copy_packages()

    # Make sure it is really there.
    dest_wcs = api.package(DEST, 'wcsaxes')
    assert "0.9" in dest_wcs['versions']

    # Remove it...
    api.remove_release(DEST, 'wcsaxes', "0.9")
    # ...and make sure it is really gone.
    dest_wcs = api.package(DEST, 'wcsaxes')
    assert "0.9" not in dest_wcs['versions']
