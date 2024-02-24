#!/usr/bin/env python3

from collections import namedtuple
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import tarfile
import platform
import subprocess
import sys
import re
import os
import json

# URLs for accessing data on GitHub.
GH_API_URL='https://api.github.com/repos/'
GH_RAW_URL='https://raw.githubusercontent.com/'

# URLs for retrieving current versions of Perseus and Rust.
PERSEUS_URL='{0}framesurge/perseus/releases'.format(GH_API_URL)
RUST_URL='{0}rust-lang/rust/releases'.format(GH_API_URL)

# URLs for binary dependencies of Perseus.
BINARYEN_URL='{0}WebAssembly/binaryen/releases'.format(GH_API_URL)
BONNIE_URL='{0}arctic-hen7/bonnie/releases'.format(GH_API_URL)
ESBUILD_URL='{0}evanw/esbuild/releases'.format(GH_API_URL)
WASM_PACK_URL='{0}rustwasm/wasm-pack/releases'.format(GH_API_URL)

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

FEDORA_PKG_URL='https://koji.fedoraproject.org/kojihub'

ROCKY_PKG_URL=[
    'https://download.rockylinux.org/pub/rocky/',
    '/devel/source/tree/Packages/'
]

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

PERSEUS_EXAMPLE_DEFAULT='showcase'
PERSEUS_CLI_DEFAULT='false'
ESBUILD_TARGET_DEFAULT='es6'
WASM_TARGET_DEFAULT='wasm32-unknown-unknown'
CARGO_NET_DEFAULT='false'

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
def get_data(data_url, req_data=None, content_type=None, req_method=None):
    if content_type is not None:
        req_headers = { 'Content-Type': '{0}'.format(content_type) }
    elif content_type is None:
        req_headers = { 'Content-Type': 'text/html; charset=utf-8' }
    if req_method is None:
        req_method = 'GET'
    try:
        req = Request(
            url=data_url,
            data=req_data,
            headers=req_headers,
            method=req_method
        )
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

# Convert a JSON object to a SimpleNamespace.
def json_to_namespace(json_obj):
    if json_obj == None:
        return None
    json_namespace = json.loads(
        json_obj,
        object_hook=lambda x:
            SimpleNamespace(**x)
    )
    return json_namespace

# Retrieve a list of tags from a remote respository.
def get_repo_tags(repo_url):
    repo_json = get_data(
        data_url='{0}'.format(repo_url),
        content_type='application/json'
    )
    repo_namespace = json_to_namespace(repo_json)
    tags = []
    for repo_release in enumerate(repo_namespace):
        version_tag = repo_release[1].tag_name
        tags.append(version_tag)
    return tags

# Retrieve only the latest tag from a remote repository.
def get_repo_latest_tag(repo_url):
    tags = get_repo_tags(repo_url)
    return tags[0]

# Retrieve the semantic version of a given distro's latest stable release.
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
        re_str = ' '.join(
            [
                '(?<=\[\`)[0-9]{1,}[\.]{1}[0-9]{1,}[\.]{1}[0-9]{1,}(?=\`,',
                '\`[0-9]{1,}[\.][0-9]{1,}\`,',
                '\`[0-9]{1,}\`,',
                '\`latest\`\])'
            ]
        )
    elif linux_name == 'debian':
        re_str = ' '.join(
            [
                '(?<=\[\`bullseye-slim\`,',
                '\`bullseye-[0-9]{8}-slim\`,',
                '\`)[0-9]{1,}[\.]{1}[0-9]{1,}-slim(?=\`,',
                '\`[0-9]{1,}-slim\`\])'
            ]
        )
    elif linux_name == 'fedora':
        re_str = ' '.join(
            [
                '(?<=\[\`)[0-9]{1,}(?=\`,',
                '\`latest\`\])'
            ]
        )
    elif linux_name == 'rocky':
        re_str = ' '.join(
            [
                '(?<=\[\`[0-9]{1,}[\.]{1}[0-9]{1,}[\.]{1}[0-9]{8}-minimal\`,',
                '\`)[0-9]{1,}[\.]{1}[0-9]{1,}-minimal(?=\`,',
                '\`[0-9]{1,}-minimal\`\])'
            ]
        )
    elif linux_name == 'ubuntu':
        re_str = ' '.join(
            [
                '(?<=\[\`)[0-9]{1,}[\.]{1}[0-9]{1,}(?=\`,',
                '\`jammy-[0-9]{8}\`,',
                '\`jammy\`,',
                '\`latest\`\])'
            ]
        )
    linux_pattern = re.compile(
        pattern = re_str
    )
    distro_latest = re.search(
        pattern = linux_pattern,
        string = '{0}'.format(distro_namespace.full_description)
    ).group(0)
    return distro_latest

# Retrieve the dependency string required for a specific package release.
def get_package_version(target, pkg):
    linux_name = '{0}'.format(target.os)
    linux_channel = '{0}'.format(target.channel)
    output_str = None
    if linux_name == 'alpine':
        rel_pat = re.compile('^[0-9]{1,}[\.]{1}[0-9]{1,}')
        sfx_str = '-stable'
        match_obj = re.search(
            pattern=rel_pat,
            string=linux_channel
        )
        match_str = '{0}{1}'.format(
            match_obj.group(0),
            sfx_str
        )
        pkg_url = '{0}{1}{2}{3}{4}'.format(
            ALPINE_PKG_URL[0],
            match_str,
            ALPINE_PKG_URL[1],
            pkg,
            ALPINE_PKG_URL[2]
        )
        pkg_data_response = get_data(
            data_url=pkg_url
        )
        pkg_data_str = ' '.join(
            pkg_data_response.splitlines()
        )
        re_pattern = [
            '(?<=pkgname=)\w+',
            '(?<=pkgver=)[^ ]{1,}',
            '(?<=pkgrel=)[^ ]{1,}'
        ]
        pkg_semver = []
        for p in re_pattern:
            pkg_pat = re.compile(p)
            match_obj = re.search(
                pattern=pkg_pat,
                string=pkg_data_str
            )
            pkg_semver.append(match_obj.group(0))
        output_str = '{0}={1}-r{2}'.format(
            pkg_semver[0],
            pkg_semver[1],
            pkg_semver[2]
        )
    elif linux_name == 'debian':
        pkg_url = '{0}{1}{2}'.format(
            DEBIAN_PKG_URL,
            pkg,
            '/'
        )
        pkg_data_response = get_data(
            data_url=pkg_url,
            content_type='application/json'
        )
        search_str = ''.join(
            [
                '(?<="suites":\["',
                linux_channel,
                '"\],"version":")',
                '[a-z0-9\.+-]{1,}',
                '(?=")'
            ]
        )
        pkg_pat = re.compile(search_str)
        match_obj = re.search(
            pattern=pkg_pat,
            string=pkg_data_response
        )
        output_str = '{0}'.format(
            match_obj.group(0)
        )
    elif linux_name == 'fedora':
        pfx_str = 'f'
        sfx_str = '-updates'
        api_tag = '{0}{1}{2}'.format(
            pfx_str,
            linux_channel,
            sfx_str
        )
        xml_req_xml = [
            '<?xml version="1.0"?>',
            '<methodCall>',
            '<methodName>',
            'getLatestBuilds',
            '</methodName>',
            '<params>',
            '<param>',
            '<value>',
            '<string>',
            api_tag,
            '</string>'
            '</value>',
            '</param>',
            '<param>',
            '<value>',
            '<nil/>',
            '</value>',
            '</param>',
            '<param>',
            '<value>',
            '<string>',
            api_tag,
            '</string>'
            '</value>',
            '</param>',
            '<param>',
            '<value>',
            '<nil/>',
            '</value>',
            '</param>',
            '</params>',
            '</methodCall>'
        ]
        xml_req_body = ''.join(xml_req_xml)
        pkg_data_response = get_data(
            data_url=FEDORA_PKG_URL,
            req_data=xml_req_body,
            content_type='text/xml',
            req_method='POST'
        )
        pkg_data_str = ''.join(
            pkg_data_response.splitlines()
        )
        pkg_pat = re.compile(
            ''.join(
                [
                    '(?<=<name>nvr</name><value><string>)',
                    '[^\ \/<>]{1,}',
                    '(?=</string></value>)'
                ]
            )
        )
        match_obj = re.search(
            pattern=pkg_pat,
            string=pkg_data_str
        )
        output_str = '{0}'.format(
            match_obj.group(0)
        )
    elif linux_name == 'rocky':
        pass
    elif linux_name == 'ubuntu':
        pass
    else:
        pass

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

# Retrieve the dependency string required for a specific Debian package release.
def get_debian_package_version(distro_series, pkg):
    # Make sure a string argument was passed to `pkg` parameter.
    api_pkg = '{0}'.format(pkg)
    # Interpolate the url for the given `pkg` argument.
    pkg_url = '{0}{1}{2}'.format(DEBIAN_PKG_URL, api_pkg, '/')
    # Retrieve the JSON returned by the url.
    pkg_json = get_data(
        data_url='{0}'.format(pkg_url),
        content_type='application/json'
    )
    # Define a pattern to match against within the retrieved JSON.
    re_pattern = re.compile(
        ''.join(
            [
                '(?<="suites":\["',
                '{0}'.format(distro_series),
                '"\],"version":")',
                '[a-z0-9\.+-]{1,}',
                '(?=")'
            ]
        )
    )
    # Store the match extracted from the JSON.
    pkg_data = re.search(
        pattern=re_pattern,
        string='{0}'.format(pkg_json)
    ).group(0)
    # Define the string to return from this function.
    pkg_version_string = '{0}'.format(pkg_data)
    # Return the expected output string.
    return pkg_version_string

# Retrieve the dependency string required for a specific Fedora package release.
def get_fedora_package_version(fedora_release, pkg):
    api_tag = "f{0}-updates".format(fedora_release)
    api_pkg = "{0}".format(pkg)
    xml_req_xml = [
        '<?xml version="1.0"?>',
        '<methodCall>',
        '<methodName>',
        'getLatestBuilds',
        '</methodName>',
        '<params>',
        '<param>',
        '<value>',
        '<string>{0}</string>'.format(api_tag),
        '</value>',
        '</param>',
        '<param>',
        '<value>',
        '<nil/>',
        '</value>',
        '</param>',
        '<param>',
        '<value>',
        '<string>{0}</string>'.format(api_pkg),
        '</value>',
        '</param>',
        '<param>',
        '<value>',
        '<nil/>',
        '</value>',
        '</param>',
        '</params>',
        '</methodCall>'
    ]
    xml_req_body = ''.join(xml_req_xml)
    xml_res_data = get_data(
        data_url=FEDORA_PKG_URL,
        req_data=xml_req_body,
        content_type='text/xml',
        req_method='POST'
    ).splitlines()
    xml_res_body = ''.join(xml_res_data)
    pkg_version_string = re.search(
        ''.join(
            [
                '(?<=<name>nvr</name><value><string>)',
                '[^\ \/<>]{1,}',
                '(?=</string></value>)'
            ]
        ),
        xml_res_body
    ).group(0)
    return pkg_version_string

# Retrieve the dependency string required for a specific Rocky package release.
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

# Retrieve the dependency string required for a specific Ubuntu package release.
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

def generate_packages_list(target):
    # 1. create a list for holding the <package_name=semver> strings.
    # 2. allocate a list of package names alphabetically in reverse.
    # 3. interpolate entries with appended " \" line continuations, except [0].
    # 4. reverse entries and append "\n" to all.
    # 5. return the resulting list.
    #
    pass
    # dest = target.os
    # package_func = None
    # package_manager = None
    # if dest == 'alpine':
    #     package_names = [
    #         'python3',
    #         'pkgconf',
    #         'perl',
    #         'openrc',
    #         'linux-headers',
    #         'gawk',
    #         'curl',
    #         'alpine-sdk'
    #     ]
    #     package_func = get_alpine_package_version
    #     package_command = [
    #         'apk update; \\\n',
    #         '\tapk add \\\n'
    #     ]
    # elif dest in ('debian', 'ubuntu'):
    #     package_names = [
    #         'python3',
    #         'pkg-config',
    #         'perl',
    #         'gawk',
    #         'curl',
    #         'build-essential',
    #         'apt-transport-https'
    #     ]
    #     if dest == 'debian':
    #         package_func = get_debian_package_version
    #     elif dest == 'ubuntu':
    #         package_func = get_ubuntu_package_version
    #     package_command = [
    #         'apt-get update; \\\n',
    #         '\tapt-get -y install --no-install-recommends \\\n'
    #     ]
    # elif dest == 'fedora':
    #     package_names = [
    #         'python3',
    #         'pkgconf',
    #         'perl',
    #         'make',
    #         'kernel-devel',
    #         'glibc'
    #         'gcc-c++',
    #         'gcc',
    #         'gawk',
    #         'curl-minimal',
    #         'automake'
    #     ]
    #     package_func = get_fedora_package_version
    #     package_command = 'dnf'
    # elif dest == 'rocky':
    #     package_names = [
    #         'python3',
    #         'pkgconf',
    #         'perl',
    #         'make',
    #         'glibc',
    #         'gcc',
    #         'gawk',
    #         'curl',
    #         'automake'
    #     ]
    #     package_func = get_rocky_package_version
    #     package_command = 'yum'
    # for i, pkg in enumerate(package_names):
    #     pkg_version = package_func(target.version, pkg)
    #     if i > 0:
    #         pkg_string = ''.join(['\t', pkg, '=', pkg_version, ' \\\n'])
    #     else:
    #         pkg_string = ''.join(['\t', pkg, '=', pkg_version, '\n'])
    #     packages.append(pkg_string)
    # packages.append('RUN {0}')
    # packages.reverse()
    # packages[0] = packages[0].replace('\t', '\tdnf -y install ')

def generate_template(target):
    file_path = '{0}/Dockerfile'.format(target.path)
    if not os.path.isfile(file_path):
        f = open(file=file_path, mode='w')
        dockerfile_contents = [
            '# Pull base image\n.',
            'FROM {0} AS base\n'.format(target.tag),
            '\n',
            '# Define optional arguments we can pass to `docker`.\n'
            'ARG EXAMPLE_NAME \\\n',
            '\tPERSEUS_VERSION \\\n',
            '\tPERSEUS_CLI_SEQUENTIAL \\\n',
            '\tBINARYEN_VERSION \\\n',
            '\tBONNIE_VERSION \\\n',
            '\tESBUILD_VERSION \\\n',
            '\tESBUILD_TARGET \\\n',
            '\tWASM_PACK_VERSION \\\n',
            '\tWASM_TARGET \\\n',
            '\tCARGO_NET_GIT_FETCH_WITH_CLI \\\n',
            '\n',
            '# Export environment variables.\n',
            '# NOTE: Setting PERSEUS_CLI_SEQUENTIAL to true is required for low memory environments.\n',
            ''.join(
                'ENV EXAMPLE_NAME="${',
                'EXAMPLE_NAME:-',
                '{0}'.format(PERSEUS_EXAMPLE_DEFAULT),
                '}" \\\n'
            ),
            'ENV EXAMPLE_NAME=\"${EXAMPLE_NAME\:-showcase}\" \\\n',
            ''.join(
                [
                    '\tPERSEUS_VERSION="${',
                    'PERSEUS_VERSION:-',
                    '{0}'.format(get_repo_latest_tag(PERSEUS_URL)),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tPERSEUS_CLI_SEQUENTIAL="${',
                    'PERSEUS_CLI_SEQUENTIAL:-',
                    '{0}'.format(PERSEUS_CLI_DEFAULT),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tBINARYEN_VERSION="${',
                    'BINARYEN_VERSION:-',
                    '{0}'.format(get_repo_latest_tag(BINARYEN_URL)),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tBONNIE_VERSION="${',
                    'BONNIE_VERSION:-',
                    '{0}'.format(get_repo_latest_tag(BONNIE_URL)),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tESBUILD_VERSION="${',
                    'ESBUILD_VERSION:-',
                    '{0}'.format(get_repo_latest_tag(ESBUILD_URL)),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tESBUILD_TARGET="${',
                    'ESBUILD_TARGET:-',
                    '{0}'.format(ESBUILD_TARGET_DEFAULT),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tWASM_PACK_VERSION="${',
                    'WASM_PACK_VERSION:-',
                    '{0}'.format(get_repo_latest_tag(WASM_PACK_URL)),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tWASM_TARGET="${',
                    'WASM_TARGET:-',
                    '{0}'.format(WASM_TARGET_DEFAULT),
                    '}" \\\n'
                ]
            ),
            ''.join(
                [
                    '\tCARGO_NET_GIT_FETCH_WITH_CLI="${',
                    'CARGO_NET_GIT_FETCH_WITH_CLI:-',
                    '{0}'.format(CARGO_NET_DEFAULT),
                    '}" \\\n'
                ]
            ),
            '\n',
            '# Work from the root of the container.\n',
            'WORKDIR /\n',
            '\n'
            '# Install build dependencies.'
        ]
        
        # TODO: write list concatenation.
        f.writelines(dockerfile_contents)

def generate_directory(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def generate_docker_files():
    perseus_latest = get_repo_latest_tag(PERSEUS_URL)
    root_path='./{0}'.format(perseus_latest)
    if not os.path.exists(root_path):
        generate_directory(root_path)
        TargetOS = namedtuple('TargetOS', ['os', 'path', 'tag'])
        alpine_latest = get_latest_distribution(ALPINE_URL)
        debian_latest = get_latest_distribution(DEBIAN_URL)
        fedora_latest = get_latest_distribution(FEDORA_URL)
        rocky_latest = get_latest_distribution(ROCKY_URL)
        ubuntu_latest = get_latest_distribution(UBUNTU_URL)
        targets = [
            TargetOS(
                os='alpine',
                path='alpine{0}'.format(alpine_latest),
                tag='alpine:{0}'.format(alpine_latest),
                version='{0}'.format(alpine_latest)
            ),
            TargetOS(
                os='debian',
                path='debian{0}'.format(debian_latest),
                tag='debian:{0}'.format(debian_latest),
                version='{0}'.format(debian_latest)
            ),
            TargetOS(
                os='fedora',
                path='fedora{0}'.format(fedora_latest),
                tag='fedora:{0}'.format(fedora_latest),
                version='{0}'.format(fedora_latest)
            ),
            TargetOS(
                os='rocky',
                path='rocky{0}'.format(rocky_latest),
                tag='rocky:{0}'.format(rocky_latest),
                version='{0}'.format(rocky_latest)
            ),
            TargetOS(
                os='ubuntu',
                path='ubuntu{0}'.format(ubuntu_latest),
                tag='ubuntu:{0}'.format(ubuntu_latest),
                version='{0}'.format(ubuntu_latest)
            )
        ]
        for target in targets:
            generate_directory(target.path)
            generate_template(target)

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