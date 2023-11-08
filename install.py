#!/usr/bin/env python3

from collections import namedtuple
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import html_to_json
import tarfile
import platform
import subprocess
import sys
import re
import os
import json
import koji # we must pip install koji to import

# URLs for accessing data on GitHub.
GH_API_URL='https://api.github.com/repos/'
GH_RAW_URL='https://raw.githubusercontent.com/'

# URLs for retrieving current versions of Perseus and Rust.
PERSEUS_URL='{0}framesurge/perseus/releases'.format(GH_API_URL)
RUST_URL='{0}rust-lang/rust/releases'.format(GH_API_URL)

# URL for the Docker Hub official image registry.
HUB_URL='https://hub.docker.com/v2/namespaces/library/repositories/'

# URLs for retrieving current versions of Linux distributions.
ALPINE_URL='{0}alpine'.format(HUB_URL)
DEBIAN_URL='{0}debian'.format(HUB_URL)
FEDORA_URL='{0}fedora'.format(HUB_URL)
ROCKY_URL='{0}rockylinux'.format(HUB_URL)
UBUNTU_URL='{0}ubuntu'.format(HUB_URL)

# URLs for retrieving current versions of Linux packages.
ALPINE_PKG_URL=[
    '{0}alpinelinux/aports/'.format(GH_RAW_URL),
    '/main/',
    'APKBUILD'
]

DEBIAN_PKG_URL='https://sources.debian.org/api/src/'

# Fedora Project provides acess to their API programmatically using
# a Python package called `koji`. We must `pip install koji` to import it.
FEDORA_PKG_URL='https://koji.fedoraproject.org/kojihub'

ROCKY_PKG_URL=[
    'https://download.rockylinux.org/pub/rocky/',
    '/BaseOS/source/tree/Packages/'
]

# We have to parse the data after it comes in.
# Unfortunately we can't scope down to a specific release channel.

# YAY!!! I finally scoped down to the precise version I need!!!
# curl -H 'Content-Type: "application/json"' -sSL 'https://api.launchpad.net/1.0/ubuntu/+archive/primary?ws.op=getPublishedSources&date_superceded=null&exact_match=true&pocket=Updates&status=Published&source_name=curl&distro_series=https%3A%2F%2Fapi.launchpad.net%2F1.0%2Fubuntu%2Fjammy' | jq

UBUNTU_PKG_URL=[
    'https://api.launchpad.net/1.0/ubuntu/+archive/primary',
    '?ws.op=getPublishedSources',
    '&date_superceded=null',
    '&distro_series=https%3A%2F%2Fapi.launchpad.net%2F1.0%2F',
    'ubuntu%2F%%DISTRO_SERIES%%',
    '&exact_match=true',
    '&pocket=Updates',
    '&status=Published',
    '&source_name='
]

# Check whether or not the host is running Linux.
# We cannot proceed unless we are on a Linux host.
def os_is_linux():
    if sys.platform.startswith('linux'):
        return True
    return False

# Retrieve data about the platform of the host.
def get_local_platform():
    platform_data = SimpleNamespace(
        os=SimpleNamespace(
            **{
                k.lower(): v for k, v in platform \
                    .freedesktop_os_release() \
                    .items()
            }
        ),
        arch=platform.machine()
    )
    return platform_data

# Request some data from a remote server.
def get_data(data_url, content_type):
    if content_type is not None:
        req_headers = { 'Content-Type': '{0}'.format(content_type) }
    elif content_type is None:
        req_headers = { 'Content-Type': 'text/html; charset=utf-8' }
    req = Request(url=data_url, headers=req_headers)
    try:
        res = urlopen(req)
    except (HTTPError, URLError) as e:
        if hasattr(e, 'code'):
            print('Server was unable to fulfill request.')
            print('Error code: {0}'.format(e.code))
        elif hasattr(e, 'reason'):
            print('Server was unreachable.')
            print('Reason: {0}'.format(e.reason))
        return None
    else:
        res_data = res.read().decode('utf-8')
        return res_data

def json_to_namespace(json_obj):
    if json_obj == None:
        return None
    json_namespace = json.loads(
        json_obj,
        object_hook=lambda x:
            SimpleNamespace(**x)
    )
    return json_namespace

# Retrieve the release version tags for Perseus.
def get_perseus_tags():
    perseus_json = get_data(
        data_url='{0}'.format(PERSEUS_URL),
        content_type='application/json'
    )
    perseus_namespace = json_to_namespace(perseus_json)
    tags = []
    for perseus_release in enumerate(perseus_namespace):
        version_tag = perseus_release[1].tag_name
        tags.append(version_tag)
    return tags

def get_perseus_latest_tag():
    tags = get_perseus_tags()
    return tags[0]

def get_latest_distribution(linux_url):
    linux_name = re.search(
        '(?<=repositories/)[a-z]{1,}',
        '{0}'.format(linux_url)
    ).group(0)
    distro_string = get_data(
        data_url='{0}'.format(linux_url),
        content_type='application/json'
    )
    distro_namespace = json_to_namespace(distro_string)
    if linux_name == 'alpine':
        re_str = '(?<=\[\`)[0-9]{1,}[\.]{1}[0-9]{1,}[\.]{1}[0-9]{1,}(?=\`, \`[0-9]{1,}[\.][0-9]{1,}\`, \`[0-9]{1,}\`, \`latest\`\])'
    elif linux_name == 'debian':
        re_str = '(?<=\[\`bullseye-slim\`, \`bullseye-[0-9]{8}-slim\`, \`)[0-9]{1,}[\.]{1}[0-9]{1,}-slim(?=\`, \`[0-9]{1,}-slim\`\])'
    elif linux_name == 'fedora':
        re_str = '(?<=\[\`)[0-9]{1,}(?=\`, \`latest\`\])'
    elif linux_name == 'rocky':
        re_str = '(?<=\[\`[0-9]{1,}[\.]{1}[0-9]{1,}[\.]{1}[0-9]{8}-minimal\`, \`)[0-9]{1,}[\.]{1}[0-9]{1,}-minimal(?=\`, \`[0-9]{1,}-minimal\`\])'
    elif linux_name == 'ubuntu':
        re_str = '(?<=\[\`)[0-9]{1,}[\.]{1}[0-9]{1,}(?=\`, \`jammy-[0-9]{8}\`, \`jammy\`, \`latest\`\])'
    distro_latest = re.search(
        '{0}'.format(re_str),
        '{0}'.format(distro_namespace.full_description)
    ).group(0)
    return distro_latest

# Retrieve the dependency string required for a specific Alpine package release.
def get_alpine_package_version(alpine_release, pkg):
    stable_alpine = '{0}-stable'.format(
        re.search(
            '^[0-9]{1,}[\.]{1}[0-9]{1,}',
            '{0}'.format(alpine_release)
        ).group(0)
    )
    pkg_url='{0}{1}{2}{3}{4}'.format(
        ALPINE_PKG_URL[0],
        stable_alpine,
        ALPINE_PKG_URL[1],
        pkg,
        ALPINE_PKG_URL[2]
    )
    pkg_data = ' '.join(
        get_data(data_url='{0}'.format(pkg_url)).splitlines()
    )
    pkg_name = re.search('(?<=pkgname=)\w+', '{0}'.format(pkg_data)).group(0)
    pkg_ver = re.search('(?<=pkgver=)[^ ]{1,}', '{0}'.format(pkg_data)).group(0)
    pkg_rel = re.search('(?<=pkgrel=)[^ ]{1,}', '{0}'.format(pkg_data)).group(0)
    pkg_version_string = "{0}={1}-r{2}".format(pkg_name, pkg_ver, pkg_rel)
    return pkg_version_string

def get_debian_package_version(distro_series, pkg):
    api_pkg = '{0}'.format(pkg)
    pkg_url = '{0}{1}{2}'.format(DEBIAN_PKG_URL, api_pkg, '/')
    pkg_json = get_data(
        data_url='{0}'.format(pkg_url),
        content_type='application/json'
    )
    re_pattern = ''.join(
        [
            '(?<="suites":\["',
            '{0}'.format(distro_series),
            '"\],"version":")',
            '[a-z0-9\.+-]{1,}',
            '(?=")'
        ]
    )
    pkg_data = re.search(
        re_pattern,
        '{0}'.format(pkg_json)
    ).group(0)
    pkg_version_string = '{0}'.format(pkg_data)
    return pkg_version_string

def get_fedora_package_version(ctx, fedora_release, pkg):
    api_tag = "f{0}-updates".format(fedora_release)
    api_pkg = "{0}".format(pkg)
    pkg_json = ctx.getLatestBuilds(
        api_tag,
        event=None,
        package=api_pkg,
        type=None
    )
    # TO DO: optimize the chained calls to replace below.
    pkg_data = ''.join('{0}'.format(pkg_json)) \
        .replace("[", "") \
        .replace("\'", "\"") \
        .replace("None", "\"\"") \
        .replace("]", "")
    pkg_namespace = json_to_namespace(pkg_data)
    pkg_version_string = '{0}'.format(pkg_namespace.nvr)
    return pkg_version_string

def get_rocky_package_version(rocky_release, pkg):
    api_tag = re.search(
        '[0-9]{1,}[\.]{1}[0-9]{1,}(?=[^ ]{0,9}-minimal)',
        '{0}'.format(rocky_release)
    ).group(0)
    api_pkg = '{0}'.format(pkg)
    api_dir = '{0}'.format(api_pkg[0])
    pkg_url = '{0}{1}{2}{3}'.format(
        ROCKY_PKG_URL[0],
        api_tag,
        ROCKY_PKG_URL[1],
        api_dir
    )
    pkg_data = ' '.join(
        get_data(
            data_url='{0}'.format(pkg_url),
            content_type=None
        ).splitlines()
    )
    pkg_version_string = re.search(
        ''.join([
            '(?<=<a\ href="',
            '{0}'.format(api_pkg),
            '-)[^ ]{1,}(?=\.src\.rpm">',
            '{0}'.format(api_pkg),
            ')'
        ]),
        '{0}'.format(pkg_data)
    ).group(0)
    return pkg_version_string

def get_ubuntu_package_version(distro_series, pkg):
    if distro_series == None:
        return None
    api_pkg = '{0}'.format(pkg)
    pkg_url = '{0}{1}'.format(''.join(UBUNTU_PKG_URL), api_pkg) \
        .replace('%%DISTRO_SERIES%%', distro_series)
    pkg_json = get_data(
        data_url='{0}'.format(pkg_url),
        content_type='application/json'
    )
    pkg_data = re.search(
        '(?<=\[)\{.*\}(?=\])',
        '{0}'.format(pkg_json)
    ).group(0)
    pkg_namespace = json_to_namespace(pkg_data)
    pkg_version_string = '{0}'.format(
        pkg_namespace.source_package_version
    )
    return pkg_version_string

def generate_template(distro, template_path):
    print('to be completed.')

def generate_dirs():
    perseus_latest = get_perseus_latest_tag()
    root_path='./{0}'.format(perseus_latest)
    if not os.path.exists(root_path):
        distributions = [
            'alpine{0}'.format(get_latest_distribution(ALPINE_URL)),
            'debian{0}'.format(get_latest_distribution(DEBIAN_URL)),
            'fedora{0}'.format(get_latest_distribution(FEDORA_URL)),
            'rocky{0}'.format(get_latest_distribution(ROCKY_URL)),
            'ubuntu{0}'.format(get_latest_distribution(UBUNTU_URL))
        ]

        for distro in distributions:
            template_path = '{0}/{1}'.format(root_path, distro)
            os.makedirs(template_path)
            generate_template(distro, template_path)

# Retrieve the target os of the build from the local environment.
def get_os_name():
    return os.getenv('TARGET_OS')

def get_os_version(perseus_version, os_name):
    # Parse the OS version based on the key of its name in `dependencies.json`.
    deps = json.load(
        open(
            'dependencies.json',
            mode='r',
            encoding='uft-8',
            errors='strict'
        )
    )
    os_version = deps[f"{perseus_version}"]['distributions'][f"{os_name}"]
    return os_version

#  Return the latest release of the distribution.
def get_os_live_version(os_name):
    print(f"placeholder")

# Each parallel job inside of the Dockerfile will use its own script(s).
# There will be no single source of truth throughout all stages of the build.

def initialize_container():
    if os_is_linux() == True:
        local_platform = get_local_platform()
        perseus_version = get_perseus_version()
        deps = json.load(
            open(
                'dependencies.json',
                mode='r',
                encoding='utf-8',
                errors='strict'
            )
        )
        data = deps[f"{perseus_version}"]
        data[f"{local_platform}"]
        # Get perseus version.
        # Use perseus and platform data to parse JSON file.
        # Generate strings from parsed JSON.
        # Run subprocess command.
        subprocess.run(
            [
                f""
            ]
        )
    return None

# Tarball downloader.
def download_tarball(remote_url, local_path):
    try:
        tgz = tarfile.open(
            fileobj=request.urlopen(remote_url),
            mode="r|gz"
        )
        tgz.extractall(path=local_path)
    except request.HTTPError as err:
        print(f"HTTP Error: {err}")
    except tarfile.ReadError as err:
        print(f"File Read Error: {err}")
    except tarfile.CompressionError as err:
        print(f"File Compression Error: {err}")
    except tarfile.StreamError as err:
        print(f"File Stream Error: {err}")
    except OSError as err:
        print(f"OS Error: {err}")
    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise

# extract tarball to /openssl.
# build openssl using subprocess.