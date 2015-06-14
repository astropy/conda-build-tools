from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

from astropy.extern.six.moves.urllib.request import urlopen
import json
import tempfile
import os
import subprocess
import xmlrpclib

DEFAULT_AFFILIATED_REGISTRY = 'http://affiliated.astropy.org/registry.json'
PYPI_JSON = 'https://pypi.python.org/pypi/{pypi_name}/json'
SKIP_AFFILIATES = ['astropysics']
PYPI_XMLRPC = 'https://pypi.python.org/pypi'


def get_affiliated_packages():
    source = urlopen(DEFAULT_AFFILIATED_REGISTRY)
    packages = json.loads(source.read())
    packages = packages['packages']
    return packages


def get_pypi_info(name):
    client = xmlrpclib.ServerProxy(PYPI_XMLRPC)
    print(client.system.listMethods())
    pypi_stable = client.package_releases(name)
    print(name, pypi_stable)
    try:
        return pypi_stable[0]
    except IndexError:
        return None


def build_affiliate_version_dict():
    packages = get_affiliated_packages()
    package_names = [p['name'] for p in packages
                     if p['name'] not in SKIP_AFFILIATES]
    print(package_names)
    package_version = {}
    for package in packages:
        name = package['name']
        if name in SKIP_AFFILIATES:
            continue
        pypi_name = package['pypi_name']
        pypi_info = get_pypi_info(pypi_name)
        package_version[pypi_name] = pypi_info
    print(package_version)
    return package_version

if __name__ == '__main__':
    versions = build_affiliate_version_dict()
    with open('requirements.txt', 'wt') as f:
        for k, v in versions.items():
            f.write('{}=={}\n'.format(k, v))
