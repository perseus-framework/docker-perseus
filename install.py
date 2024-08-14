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

# URLs for accessing data hosted on GitHub.
GH_API_URL='https://api.github.com/repos/'
GH_RAW_URL='https://raw.githubusercontent.com/'

# URLs for retrieving current versions of Perseus and Rust.
# NOTE: https://github.com/framesurge/perseus/releases/download/v0.4.2/perseus-linux-amd64
PERSEUS_URL='{pfx}framesurge/perseus/releases'.format(pfx=GH_API_URL)
RUST_URL='{pfx}rust-lang/rust/releases'.format(pfx=GH_API_URL)

# URLs for accessing binary dependencies of Perseus.
BINARYEN_URL='{pfx}WebAssembly/binaryen/releases'.format(pfx=GH_API_URL)
BONNIE_URL='{pfx}arctic-hen7/bonnie/releases'.format(pfx=GH_API_URL)
ESBUILD_URL='{pfx}evanw/esbuild/releases'.format(pfx=GH_API_URL)
WASM_PACK_URL='{pfx}rustwasm/wasm-pack/releases'.format(pfx=GH_API_URL)
RUSTUP_URL='https://sh.rustup.rs/'

# URL for the Docker Hub official image registry.
DOCKER_HUB_URL='https://hub.docker.com/v2/namespaces/library/repositories/'

# URLs for retrieving current versions of Linux distributions.
ALPINE_URL='{pfx}alpine'.format(pfx=DOCKER_HUB_URL)
DEBIAN_URL='{pfx}debian'.format(pfx=DOCKER_HUB_URL)
FEDORA_URL='{pfx}fedora'.format(pfx=DOCKER_HUB_URL)
ROCKY_URL='{pfx}rockylinux'.format(pfx=DOCKER_HUB_URL)
UBUNTU_URL='{pfx}ubuntu'.format(pfx=DOCKER_HUB_URL)

# URLs for retrieving current versions of Alpine Linux packages.
ALPINE_PKG_URL=[
    '{pfx}alpinelinux/aports/'.format(pfx=GH_RAW_URL),
    '/main/',
    'APKBUILD'
]

# URLs for retrieving current versions of Debian Linux packages.
DEBIAN_PKG_URL='https://sources.debian.org/api/src/'

# URLs for retrieving current versions of Fedora Linux packages.
FEDORA_PKG_URL='https://koji.fedoraproject.org/kojihub'

# URLs for retrieving current versions of Rockylinux packages.
ROCKY_PKG_URL=[
    'https://download.rockylinux.org/pub/rocky/',
    '/devel/source/tree/Packages/'
]

# URLs for retrieving current versions of Ubuntu Linux packages.
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

# Environment variable default values for use with `docker` CLI.
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

# Retrieve platform data from the Linux host in object form.
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

# Request arbitrary data from a remote server using 'GET' method.
def get_data(data_url, req_data=None, content_type=None, req_method=None):
    if content_type is not None:
        req_headers = { 'Content-Type': '{ct}'.format(ct=content_type) }
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
            print('Error code: {ec}'.format(ec=e.code))
        elif hasattr(e, 'reason'):
            print('Server was unreachable.')
            print('Reason: {er}'.format(er=e.reason))
        return None
    else:
        res_data = res.read().decode('utf-8')
        return res_data

# Convert a JSON object to a SimpleNamespace.
# This is useful to preserve expected key, value pairs.
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
        data_url='{ru}'.format(ru=repo_url),
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
        data_url='{lu}'.format(lu=linux_url),
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
        string = '{fd}'.format(fd=distro_namespace.full_description)
    ).group(0)
    return distro_latest

# Retrieve the dependency string required for a specific package release.
def get_package_version(target, pkg):
    linux_name = '{ln}'.format(ln=target.os)
    linux_channel = '{lc}'.format(lc=target.channel)
    output_str = None
    if linux_name == 'alpine':
        rel_pat = re.compile('^[0-9]{1,}[\.]{1}[0-9]{1,}')
        sfx_str = '-stable'
        match_obj = re.search(
            pattern=rel_pat,
            string=linux_channel
        )
        match_str = '{m}{sfx}'.format(
            m=match_obj.group(0),
            sfx=sfx_str
        )
        pkg_url = '{p0}{m}{p1}{pkg}{p2}'.format(
            p0=ALPINE_PKG_URL[0],
            m=match_str,
            p1=ALPINE_PKG_URL[1],
            pkg=pkg,
            p2=ALPINE_PKG_URL[2]
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
        output_str = '{pkg}={ver}-r{rel}'.format(
            pkg=pkg_semver[0],
            ver=pkg_semver[1],
            rel=pkg_semver[2]
        )
    elif linux_name == 'debian':
        pkg_url = '{d}{p}{s}'.format(
            d=DEBIAN_PKG_URL,
            p=pkg,
            s='/'
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
        output_str = '{m}'.format(
            m=match_obj.group(0)
        )
    elif linux_name == 'fedora':
        pfx_str = 'f'
        sfx_str = '-updates'
        api_tag = '{pfx}{lc}{sfx}'.format(
            pfx=pfx_str,
            lc=linux_channel,
            sfx=sfx_str
        )
        # Format our request as an XML heredoc that Fedora's API can consume.
        xml_req_xml = '''
<?xml version="1.0"?><methodCall><methodName>getLatestBuilds</methodName><params><param><value><string>%%API_TAG%%</string></value></param><param><value><nil/></value></param><param><value><string>%%API_TAG%%</string></value></param><param><value><nil/></value></param></params></methodCall>
'''
        xml_req_body = xml_req_xml.strip().replace(
            '%%API_TAG%%',
            api_tag
        )
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
        output_str = '{m}'.format(
            m=match_obj.group(0)
        )
    elif linux_name == 'rocky':
        api_pat = re.compile(
            '[0-9]{1,}[\.]{1}[0-9]{1,}(?=[^ ]{0,9}-minimal)'
        )
        match_obj = re.search(
            pattern=api_pat,
            string=linux_channel
        )
        match_str = '{0}'.format(
            match_obj.group(0)
        )
        api_dir = pkg[0]
        pkg_url = '{p0}{m}{p1}{a}'.format(
            p0=ROCKY_PKG_URL[0],
            m=match_str,
            p1=ROCKY_PKG_URL[1],
            a=api_dir
        )
        pkg_data_response = get_data(
            data_url=pkg_url,
            content_type=None
        )
        pkg_data_str = ' '.join(
            pkg_data_response.splitlines()
        )
        pkg_pat = re.compile(
            ''.join(
                [
                    '(?<=<a\ href="',
                    pkg,
                    '-)[^ ]{1,}(?=\.src\.rpm">',
                    pkg,
                    ')'
                ]
            )
        )
        match_obj = re.search(
            pattern=pkg_pat,
            string=pkg_data_str
        )
        output_str = '{m}'.format(
            m=match_obj.group(0)
        )
    elif linux_name == 'ubuntu':
        pkg_url = '{pu}{pkg}'.format(
            pu=''.join(UBUNTU_PKG_URL),
            pkg=pkg
        ).replace(
            '%%DISTRO_SERIES%%',
            linux_channel
        )
        pkg_data_response = get_data(
            data_url=pkg_url,
            content_type='application/json'
        )
        pkg_pat = re.compile(
            '(?<=\[)\{.*\}(?=\])'
        )
        match_obj = re.search(
            pattern=pkg_pat,
            string=pkg_data_response
        )
        match_str = '{m}'.format(
            m=match_obj.group(0)
        )
        pkg_ns = json_to_namespace(match_str)
        output_str = '{spv}'.format(
            spv=pkg_ns.source_package_version
        )
    return output_str

# Generate the list of packages to be used in the Dockerfile.
def generate_dockerfile_packages_list(target):
    dest = target.os
    package_names = None
    if dest == 'alpine':
        package_names = [
            'python3',
            'pkgconf',
            'perl',
            'openrc',
            'linux-headers',
            'git',
            'gawk',
            'curl',
            'alpine-sdk'
        ]
    elif dest in ('debian', 'ubuntu'):
        package_names = [
            'python3',
            'pkg-config',
            'perl',
            'git',
            'gawk',
            'curl',
            'build-essential',
            'apt-transport-https'
        ]
    elif dest == 'fedora':
        package_names = [
            'python3',
            'pkgconf',
            'perl',
            'make',
            'kernel-devel',
            'glibc',
            'git',
            'gcc-c++',
            'gcc',
            'gawk',
            'curl-minimal',
            'automake'
        ]
    elif dest == 'rocky':
        package_names = [
            'python3',
            'pkgconf',
            'perl',
            'make',
            'glibc',
            'git',
            'gcc',
            'gawk',
            'curl',
            'automake'
        ]
    if package_names is None:
        # Exit early (failure condition).
        return None
    output_list = []
    # Iterate over the packages and prepend tab, append backslash.
    # NOTE: first item becomes last item after call to str.reverse() below.
    for i, pkg in enumerate(package_names):
        pkg_version = get_package_version(target, pkg)
        pkg_string = [
            R'\t',
            pkg,
            R'=',
            pkg_version,
            R' \\'
        ]
        # Append a semicolon after the first (actually last) item.
        # NOTE: This is required syntax when using a multi-line compound
        # command statement in shell script.
        if i == 0:
            pkg_string[4] = R'; \\'
        output_list.append(R''.join(pkg_string))
    # Reverse packages to be listed in proper alphabetical order.
    output_list.reverse()
    return output_list

def generate_rustup_commands():
    output_rustup = [
        R'\tcurl %s -sSf | sh -s -- -y --target %s;' % \
            (RUSTUP_URL, WASM_TARGET_DEFAULT),
        R''
    ]
    return output_rustup

# Output all build dependency commands required for the base image.
def generate_dockerfile_base_run(target):
    linux_name = '{ln}'.format(ln=target.os)
    if linux_name == 'alpine':
        base_run = [
            R'RUN apk update; \\',
            R'\tapk add \\'
        ]
    elif linux_name in ('debian', 'ubuntu'):
        base_run = [
            R'RUN apt-get update; \\',
            R'\tapt-get -y --no-install-recommends install \\'
        ]
    elif linux_name == 'fedora':
        base_run = [
            R'RUN dnf -y update; \\',
            R'\tdnf -y --allowerasing --nodocs install \\'
        ]
    elif linux_name == 'rocky':
        base_run = [
            R'RUN microdnf -y update; \\',
            R'\tmicrodnf -y --nodocs install \\'
        ]
    if base_run is None:
        # Failure condition.
        return None
    pkg_list = generate_dockerfile_packages_list(target)
    rustup_commands = generate_rustup_commands()
    output_base_run = [
        R'# Install build dependencies.',
        *base_run,
        *pkg_list,
        *rustup_commands
    ]
    return output_base_run

def generate_dockerfile_from_base(target):
    output_from_base = [
        R'# Pull base image',
        R'FROM %s AS base' % (target.tag),
        R''
    ]
    return output_from_base

def generate_dockerfile_args():
    output_args = [
        R'# Define optional arguments we can pass to `docker`.',
        R'ARG EXAMPLE_NAME \\',
        R'\tPERSEUS_VERSION \\',
        R'\tPERSEUS_CLI_SEQUENTIAL \\',
        R'\tBINARYEN_VERSION \\',
        R'\tBONNIE_VERSION \\',
        R'\tESBUILD_VERSION \\',
        R'\tESBUILD_TARGET \\',
        R'\tWASM_PACK_VERSION \\',
        R'\tWASM_TARGET \\',
        R'\tCARGO_NET_GIT_FETCH_WITH_CLI \\',
        '',
    ]
    return output_args

def generate_dockerfile_env_vars():
    output_env_vars = [
        R'# Export environment variables.',
        R'# NOTE: Setting PERSEUS_CLI_SEQUENTIAL to true',
        R'# is required for low memory environments.',
        R'ENV EXAMPLE_NAME=${EXAMPLE_NAME:-%s} \\' % \
            (PERSEUS_EXAMPLE_DEFAULT),
        R'\tPERSEUS_VERSION=${PERSEUS_VERSION:-%s} \\' % \
            (get_repo_latest_tag(PERSEUS_URL)),
        R'\tPERSEUS_CLI_SEQUENTIAL=${PERSEUS_CLI_SEQUENTIAL:-%s} \\' % \
            (PERSEUS_CLI_DEFAULT),
        R'\tBINARYEN_VERSION=${BINARYEN_VERSION:-%s} \\' % \
            (get_repo_latest_tag(BINARYEN_URL)),
        R'\tBONNIE_VERSION=${BONNIE_VERSION:-%s} \\' % \
            (get_repo_latest_tag(BONNIE_URL)),
        R'\tESBUILD_VERSION=${ESBUILD_VERSION:-%s} \\' % \
            (get_repo_latest_tag(ESBUILD_URL)),
        R'\tESBUILD_TARGET=${ESBUILD_TARGET:-%s} \\' % \
            (ESBUILD_TARGET_DEFAULT),
        R'\tWASM_PACK_VERSION=${WASM_PACK_VERSION:-%s} \\' % \
            (get_repo_latest_tag(WASM_PACK_URL)),
        R'\tWASM_TARGET=${WASM_TARGET:-%s} \\' % \
            (WASM_TARGET_DEFAULT),
        R'\t%s=%s%s%s' % \
            (
                R'CARGO_NET_GIT_FETCH_WITH_CLI',
                R'${CARGO_NET_GIT_FETCH_WITH_CLI:-',
                CARGO_NET_DEFAULT,
                R'}'
            ),
        R''
    ]
    return output_env_vars

def generate_dockerfile_base_workdir():
    output_base_workdir = [
        R'# Work from the root of the container.',
        R'WORKDIR /',
        R''
    ]
    return output_base_workdir

def generate_dockerfile_base(target):
    from_base = generate_dockerfile_from_base(target)
    args = generate_dockerfile_args()
    env_vars = generate_dockerfile_env_vars()
    base_workdir = generate_dockerfile_base_workdir()
    base_run = generate_dockerfile_base_run(target)
    output_dockerfile_base = [
        *from_base,
        *args,
        *env_vars,
        *base_workdir,
        *base_run
    ]
    return output_dockerfile_base

def generate_dockerfile_binaryen():
    output_binaryen = [
        R'# Create a build stage for `binaryen` we can run in parallel.',
        R'FROM base AS binaryen',
        R'',
        R'# Work from the chosen install path for `binaryen`.',
        R'WORKDIR /binaryen',
        R'',
        R'# Download, extract, and remove compressed tar of `binaryen`.',
        R'RUN curl \\',
        R'\t--progress-bar \\',
        R'\t-Lo binaryen-${BINARYEN_VERSION}.tar.gz \\',
        R'\t%s%s%s; \\' % \
        (
            BINARYEN_URL,
            R'/download/version_${BINARYEN_VERSION}',
            R'/binaryen-version_${BINARYEN_VERSION}-x86_64-linux.tar.gz'
        ),
        R'\ttar \\',
        R'\t--strip-components=1 \\',
        R'\t-xzf binaryen-${BINARYEN_VERSION}.tar.gz; \\',
        R'\trm -f binaryen-${BINARYEN_VERSION}.tar.gz;',
        R''
    ]
    return output_binaryen

def generate_dockerfile_bonnie():
    output_bonnie = [
        R'# Create a build stage for `bonnie` we can run in parallel.',
        R'FROM base AS bonnie',
        R'',
        R'# Work from the chosen install path for `bonnie`.',
        R'WORKDIR /bonnie',
        R'',
        R'# Install crate `bonnie` into the work path.',
        R'RUN cargo install bonnie --version ${BONNIE_VERSION}; \\',
        R'\tmv /usr/local/cargo/bin/bonnie .;',
        R''
    ]
    return output_bonnie

def generate_dockerfile_esbuild():
    es_pat = re.compile('.*(?=/releases)')
    es_match = re.search(
        pattern=es_pat,
        string=ESBUILD_URL
    )
    ESBUILD_ROOT = R'%s' % (es_match.group(0))
    output_esbuild = [
        R'# Create a build stage for `esbuild` we can run in parallel.',
        R'FROM base AS esbuild',
        R'',
        R'# Work from the chosen install path for `esbuild`.',
        R'WORKDIR /esbuild',
        R'',
        R'# Download, extract, and remove compressed tar of `esbuild`.',
        R'RUN curl \\',
        R'\t--progress-bar \\',
        R'\t-Lo esbuild-${ESBUILD_VERSION}.tar.gz \\',
        R'\t%s%s%s; \\' % \
        (
            ESBUILD_ROOT,
            '/tarball',
            '/${ESBUILD_VERSION}'
        ),
        R'\ttar \\',
        R'\t--strip-components=1 \\',
        R'\t-xzf esbuild-${ESBUILD_VERSION}.tar.gz; \\',
        R'\trm -f esbuild-${ESBUILD_VERSION}.tar.gz;',
        R''
    ]
    return output_esbuild

def generate_dockerfile_wasm_pack():
    output_wasm_pack = [
        R'# Create a build stage for `wasm-pack` that we can run in parallel.',
        R'FROM base AS wasm-pack',
        R'',
        R'# Work from the chosen install path for `wasm-pack`.',
        R'WORKDIR /wasm-pack',
        R'',
        R'# Install crate `wasm-pack` into the work path.',
        R'RUN cargo install wasm-pack --version ${WASM_PACK_VERSION}; \\',
        R'\tmv /usr/local/cargo/bin/wasm-pack .;',
        R''
    ]
    return output_wasm_pack

def generate_dockferfile_framework():
    # TODO: Write Python command required for conditional modifications.
    fw_pat = re.compile('.*(?=/releases)')
    fw_match = re.search(
        pattern=fw_pat,
        string=PERSEUS_URL
    )
    PERSEUS_ROOT = R'%s' % (fw_match.group(0))
    output_framework = [
        R'# Create a build stage for the codebase we can run in parallel.',
        R'FROM base AS framework',
        R'',
        R'# Copy our script for conditional patching into our build layer.',
        R'COPY patch_framework.py /perseus/patch_framework.py',
        R'',
        R'# Work from the root of the codebase.',
        R'WORKDIR /perseus',
        R'',
        R'# Download the codebase and make conditional modifications.',
        R'RUN curl --progress-bar \\',
        R'\t-L %s%s%s \\' % \
        (
            PERSEUS_ROOT,
            R'/tarball',
            R'/${PERSEUS_VERSION} \\'
        ),
        R'\t| tar -xz --strip-components=1; \\',
        R'\tchmod 0755 /perseus/patch_framework.py; \\',
        R'\tpython3 /perseus/patch_framework.py;',
        R''
    ]
    return output_framework

def generate_dockerfile_perseus_cli():
    output_perseus_cli = [
        R'# Create a build stage for `perseus-cli` we can run in parallel.',
        R'FROM framework AS perseus-cli',
        R'',
        R'# Copy `bonnie` to satisfy implementation.',
        R'COPY --from=bonnie /bonnie/bonnie /usr/bin/',
        R'',
        R'# Work from the root of the codebase.',
        R'WORKDIR /perseus',
        R'',
        R'# Compile the release binary target of package `perseus-cli`.',
        R'RUN bonnie setup',
        R''
    ]
    return output_perseus_cli

def generate_dockerfile_builder():
    output_builder = [
        R'# Create a build stage for building our app we can run in parallel.',
        R'FROM framework AS builder',
        R'',
        R'# Copy the tools we previously prepared in parallel.',
        R'COPY --from=binaryen /binaryen/bin/ /usr/bin/',
        R'COPY --from=binaryen /binaryen/include/ /usr/include/',
        R'COPY --from=binaryen /binary/lib/ /usr/lib/',
        R'COPY --from=esbuild /esbuild/bin/esbuild /usr/bin/',
        R'COPY --perseus-cli /perseus/target/release/perseus /usr/bin/',
        R'COPY --from=wasm-pack /wasm-pack/wasm-pack /usr/ibn/',
        R'',
        R'# Work from the root of our app.',
        R'WORKDIR /perseus/examples/fetching',
        R''
    ]
    # TODO: populate logic required to prepare and build arbitrary app.
    return output_builder

def generate_dockerfile_app(target):
    output_deploy_image = [
        R'# Prepare the final image where the app will be deployed.',
        R'FROM %s' % (target.tag),
        R'',
        R'# Work from a chosen install path for the deployed app.',
        R'WORKDIR /app',
        R''
        R'# Copy the app into its chosen install path.',
        R'COPY --from=builder /perseus/examples/fetching/pkg /app/',
        R'',
        R'# Bind the server to `localhost` and the container to port 8080.',
        R'ENV PERSEUS_HOST=0.0.0.0 \\',
        R'\tPERSEUS_PORT=8080',
        R'',
        R'# Configure the container to serve the deployed app while running.',
        R'CMD ["./server"]'
    ]
    return output_deploy_image

# TODO: Create patch_framework.py script file we can include in build layer.

def generate_template(target):
    pass
    # file_path = R'%s/Dockerfile' % (target.path)
    # if not os.path.isfile(file_path):
    #     f = open(file=file_path, mode='w')
    #     # TODO: write list concatenation.
    #     f.writelines(dockerfile_contents)

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