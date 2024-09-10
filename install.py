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
import glob

# URLs for accessing data hosted on GitHub.
GH_API_URL='https://api.github.com/repos'
GH_RAW_URL='https://raw.githubusercontent.com'

# URL for accessing the API of crates.io.
CRATES_IO_URL='https://crates.io/api/v1/crates'

# URLs for retrieving current versions of Perseus and Rust.
PERSEUS_URL='{pfx}/framesurge/perseus/releases'.format(pfx=GH_API_URL)
RUST_URL='{pfx}/rust-lang/rust/releases'.format(pfx=GH_API_URL)

# URLs for accessing binary dependencies of Perseus.
BINARYEN_URL='{pfx}/WebAssembly/binaryen/releases'.format(pfx=GH_API_URL)
BONNIE_URL='{pfx}/arctic-hen7/bonnie/releases'.format(pfx=GH_API_URL)
ESBUILD_URL='{pfx}/evanw/esbuild/releases'.format(pfx=GH_API_URL)
WASM_PACK_URL='{pfx}/rustwasm/wasm-pack/releases'.format(pfx=GH_API_URL)
RUSTUP_URL='https://sh.rustup.rs'

# URL for the Docker Hub official image registry.
DOCKER_HUB_URL='https://hub.docker.com/v2/namespaces/library/repositories'

# URLs for retrieving current versions of Linux distributions.
ALPINE_URL='{pfx}/alpine'.format(pfx=DOCKER_HUB_URL)
DEBIAN_URL='{pfx}/debian'.format(pfx=DOCKER_HUB_URL)
FEDORA_URL='{pfx}/fedora'.format(pfx=DOCKER_HUB_URL)
ROCKY_URL='{pfx}/rockylinux'.format(pfx=DOCKER_HUB_URL)
UBUNTU_URL='{pfx}/ubuntu'.format(pfx=DOCKER_HUB_URL)

# URLs for retrieving current versions of Alpine Linux packages.
ALPINE_PKG_URL=[
    '{pfx}/alpinelinux/aports/'.format(pfx=GH_RAW_URL),
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

# Parse a repo's 'releases' API route into a URL to its tarball.
def get_tarball_url(repo_url, env_var):
    tb_pat = re.compile('.*(?=/releases)')
    tb_match = re.search(
        pattern=tb_pat,
        string=repo_url
    )
    tb_url = R'%s%s%s%s%s' % \
    (
        tb_match.group(0),
        R'/tarball',
        R'/${',
        env_var,
        R'}'
    )
    return tb_url

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

# Find all instances of a given file that are currently present.
def find_all_of_file(file_name, path_root='/'):
    if file_name is None:
        # Failure condition.
        # TODO: Add error handling - must provide file_name.
        return None
    elif path_root == '/':
        # Failure condition.
        # TODO: add error handling - path cannot be root ('/').
        return None
    # Parse the path provided, if any.
    if path_root[0] != '/':
        # Prepend the required '/' for the path to be valid.
        path_root = R'/%s' % (path_root)
    if path_root[ len(path_root) - 1 ] != '/':
        # Append the required '/' for the path to be valid.
        path_root = R'%s/' % (path_root)
    # Check to see if the path is valid.
    if os.path.exists(path_root) != True:
        # Failure condition.
        # TODO: Add error handling - path_root must exist.
        return None
    # Recursively search for all matching files.
    paths_to_file_name = glob.glob(
        R'%s**/%s' % (path_root, file_name),
        recursive=True
    )
    # Return the list of paths to all matching files found.
    return paths_to_file_name

# Parse out the names of all dependencies in a Cargo.toml file.
# NOTE: This function is provided only for completeness, but has been
#       replaced by `upgrade_cargo_toml()`.
def get_cargo_toml_dependencies(toml_path):
    if toml_path is None:
        # Failure condition.
        # TODO: Add error handling.
        return None
    # Open the Cargo.toml file in read-only mode.
    with open(
        file=toml_path,
        mode='r'
    ) as ct:
        line_is_dep = False
        output_deps = []
        # Iterate across the lines of the Cargo.toml file.
        for line in ct:
            l_str = line.strip()
            # Activate retrieval of dependency names.
            if l_str == '[dependencies]' and not line_is_dep:
                line_is_dep = True
            # Deactivate retrieval of dependency names.
            elif l_str == '' and line_is_dep:
                line_is_dep = False
            # Conditionally retrieve dependency names if activated.
            if l_str != '[dependencies]' and line_is_dep:
                # Search for valid dependency information.
                dep_pat = re.compile('^([^ ]{1,}) = (.*)$')
                dep_mat = re.search(
                    pattern=dep_pat,
                    string=l_str
                )
                # If we have found a dependency...
                if dep_mat:
                    # Search through its version information.
                    dep_version = dep_mat.group(2)
                    ignore_pat = re.compile('path = [\'"]{1}')
                    ignore_mat = re.search(
                        pattern=ignore_pat,
                        string=dep_version
                    )
                    # If the dependency is not local to the project...
                    if not ignore_mat:
                        # Append its name to the list of dependency names.
                        output_deps.append(dep_mat.group(1))
    # Return the list of dependency names.
    return output_deps

# Scan the API data for a given crate to see if the given version is yanked.
def crate_is_yanked(crate_name, crate_version):
    # TODO: handle errors from improper arguments.
    # Define the API route used to return published version information.
    crate_yank_route = R'%s/%s/versions' % (CRATES_IO_URL, crate_name)
    # Return the JSON of the given crate's releases.
    yank_json = get_data(
        data_url=crate_yank_route,
        content_type='application/json',
        req_method='GET'
    )
    # Convert the JSON string into a SimpleNamespace object.
    yank_obj = json_to_namespace(yank_json)
    # Optimistic default that the given release has not been yanked.
    is_yanked = False
    # Optimistic default that the latest release is always newer.
    latest_is_newer = True
    # Iterate across all published versions.
    for i, v in enumerate(yank_obj.versions):
        # Look for the given release as extracted from a Cargo.toml file.
        # We must check whether the supplied version is in M.m.p format.
        if crate_version.count('.') < 2:
            chk_pat = re.compile(R'^%s\.' % (crate_version))
        else:
            chk_pat = re.compile(R'^%s' % (crate_version))
        chk_mat = re.search(
            pattern=chk_pat,
            string=v.num
        )
        # If we have found a match...
        if chk_mat:
            # If this is the latest release...
            if i == 0 and latest_is_newer:
                # Indicate that the latest release semver is not newer.
                latest_is_newer = False
            # If the given release has been yanked...
            if v.yanked:
                # If the latest release is newer than the yanked one...
                if latest_is_newer:
                    # Update our return value to true.
                    is_yanked = True
            # Stop looking once we have found a match.
            break
    # Return a true or false based on whether the release was yanked.
    return is_yanked

# Retrieve the value of the `max_stable_version` field for a given crate.
def get_crate_latest_version(crate_name):
    if crate_name is None:
        # Failure condition.
        # TODO: Add error handling.
        return None
    output_latest_version = None
    crate_api_route = R'%s?q=%s' % (CRATES_IO_URL, crate_name)
    crate_json = get_data(
        data_url=crate_api_route,
        content_type='application/json',
        req_method='GET'
    )
    api_obj = json_to_namespace(crate_json)
    if api_obj.crates[0].exact_match and \
        api_obj.crates[0].name == crate_name:
        output_latest_version = api_obj.crates[0].max_stable_version
    return output_latest_version

# Upgrade dependency versions in a single Cargo.toml file.
def upgrade_cargo_toml(toml_path):
    with open(file=toml_path, mode='r') as ct:
        toml = ct.readlines()
    dependencies_pat = re.compile('\[dependencies\]\n')
    dependencies_exist = re.search(
        pattern=dependencies_pat,
        string=''.join(toml)
    )
    patch_pat = re.compile('\[patch.crates-io\]\n')
    patch_exists = re.search(
        pattern=patch_pat,
        string=''.join(toml)
    )
    if dependencies_exist is None or patch_exists is not None:
        # Failure condition.
        # No dependencies block is present in this Cargo.toml file.
        # OR, we have already patched it.
        return
    # Otherwise, we continue processing.
    patched_deps = []
    upgrades_found = False
    dep_start = toml.index('[dependencies]\n')
    try:
        # Try to find the next blank line at the end of the dependencies block.
        dep_end = toml.index('\n', dep_start)
    except:
        # If no blank line is found, the dependencies block terminates at EOF.
        dep_end = len(toml) - 1
    # Define characters that could be present in a semver string.
    ver_chars = R'\^~<>=\*, 0-9\.a-z-'
    for i in range(dep_start + 1, dep_end):
        crate_name = None
        crate_version = None
        # If this line is not a comment/commented dependency...
        if toml[i][0] != '#':
            # Check for the presence of an object in the manifest data.
            curly_pat = re.compile('^.*\{')
            curly_mat = re.search(
                pattern=curly_pat,
                string=toml[i].strip()
            )
            # If this dependency does not contain an object...
            if curly_mat is None:
                # Extract the dependency name and the semver string.
                crate_pat = re.compile(
                    R'^([_a-z-]{1,}) = "([%s]{1,})"$' % \
                    (ver_chars)
                )
                crate_mat = re.search(
                    pattern=crate_pat,
                    string=toml[i].strip()
                )
                # If we successfully parsed a crate name and version...
                if crate_mat:
                    # Store them for later use in the upgrade process.
                    crate_name = crate_mat.group(1)
                    crate_version = crate_mat.group(2)
            else:
                # This dependency contains an object.
                # We must check for the presence of a local relative path.
                # NOTE: Local relative paths are NOT upgraded.
                path_pat = re.compile('^.*(path = "[^ ]{1,}")')
                path_mat = re.search(
                    pattern=path_pat,
                    string=toml[i].strip()
                )
                # If this dependency has no local relative path...
                if path_mat is None:
                    # Extract the dependency name and the object semver string.
                    crate_pat = re.compile(
                        R'^([_a-z-]{1,}) = {.*version = "([%s]{1,})".*}$' % \
                        (ver_chars)
                    )
                    crate_mat = re.search(
                        pattern=crate_pat,
                        string=toml[i].strip()
                    )
                    # If we successfully parsed a crate name and version...
                    if crate_mat:
                        # Store them for later use in the upgrade process.
                        crate_name = crate_mat.group(1)
                        crate_version = crate_mat.group(2)
        # If we have crate information waiting to be processed...
        if crate_name and crate_version:
            # If the crate version in the Cargo.toml file has been yanked...
            if crate_is_yanked(crate_name, crate_version):
                # Extract the max_stable_version of crate over the network.
                crate_upgrade = get_crate_latest_version(crate_name)
                # If the patched depdencies list is empty...
                if len(patched_deps) == 0:
                    # Append the [patch] block as the first element.
                    patched_deps.append('[patch.crates-io]\n')
                # Append the dependency to be patched.
                patched_deps.append('%s = { version = "%s" }\n' % \
                                    (
                                        crate_name,
                                        crate_upgrade
                                    )
                )
                # If we have not yet identified any upgrades to apply...
                if upgrades_found == False:
                    # Reflect that we have identified at least one upgrade.
                    upgrades_found = True
    # If any upgrades were identified...
    if upgrades_found:
        # Append an empty new line as the last member of the [patch] block.
        patched_deps.append('\n')
        # Define the new toml syntax of the upgraded file.
        new_toml = [
            *toml[0:dep_start],
            *patched_deps,
            *toml[dep_start:]
        ]
        # Overwrite the original Cargo.toml file with the upgraded one.
        with open(file=toml_path, mode='w') as ct:
            ct.writelines(new_toml)

# Perform dependency version upgrades as one batch process.
def upgrade_all_dependencies(project_path):
    if os.path.exists(path=project_path):
        os.chdir(path=project_path)
        paths = find_all_of_file(
            file_name='Cargo.toml',
            path_root=project_path
        )
        for p in paths:
            upgrade_cargo_toml(p)

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
            'ca-certificates',
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
            'ca-certificates',
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
            'ca-certificates',
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
            'ca-certificates',
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

#
# TODO: Update `curl` and `tar` to utilize streamed tarballs with retries.
# NOTE: This will depricate removal of downloaded tar files via `rm -f`.
#

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
        R'\t-L %s \\' % \
        (
            get_tarball_url(BINARYEN_URL, 'BINARYEN_VERSION')
        ),
        R'\t| tar -C $PWD -xz --strip-components=1',
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
        R'RUN cargo install bonnie \\',
        R'\t--version ${BONNIE_VERSION} \\',
        R'\t--root $PWD \\',
        R'\t--locked;',
        R''
    ]
    return output_bonnie

def generate_dockerfile_esbuild():
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
        R'\t-L %s \\' % \
        (
            get_tarball_url(ESBUILD_URL, 'ESBUILD_VERSION')
        ),
        R'\t| tar -C $PWD -xz --strip-components=1',
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
        R'RUN cargo install wasm-pack \\',
        R'\t--version ${WASM_PACK_VERSION} \\',
        R'\t--root $PWD \\',
        R'\t--locked',
        R''
    ]
    return output_wasm_pack

def generate_dockferfile_framework():
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
        R'\t-L %s \\' % \
        (
            get_tarball_url(PERSEUS_URL, 'PERSEUS_VERSION')
        ),
        R'\t| tar -xz --strip-components=1; \\',
        R'\tchmod 0700 /perseus/patch_framework.py; \\',
        R'\tpython3 /perseus/patch_framework.py;',
        R''
    ]
    return output_framework

def generate_dockerfile_example(semver_override):
    # Instruct the Dockerfile to use the PERSEUS_VERSION env var by default.
    src_string = R'/${PERSEUS_VERSION} \\'
    # If the build process has detected the need to override the release we
    # source the example(s) from...
    if semver_override is not None:
        # Instruct the Dockerfile to use the override instead.
        src_string = R'/%s \\' % (semver_override)
    # Parse the PERSEUS_URL string to point to the root of the repository.
    ex_pat = re.compile('.*(?=/releases)')
    ex_match = re.search(
        pattern=ex_pat,
        string=PERSEUS_URL
    )
    EXAMPLE_ROOT = R'%s' % (ex_match.group(0))
    # Define the Dockerfile syntax used to pull in the example(s) we need.
    output_example = [
        R'# Create a build stage for the examples we can run in parallel.',
        R'FROM base AS examples',
        R'',
        R'# Work from the chosen path for examples.',
        R'WORKDIR /examples',
        R'',
        R'# Download the tarball of the examples.',
        R'RUN curl --progress-bar \\',
        R'\t-L %s%s%s \\' % \
        (
            EXAMPLE_ROOT,
            R'/tarball',
            src_string
        ),
        R'\t| tar -C /examples/fetching -xz --strip-components=3 \\',
        R'\tperseus-%s/examples/fetching;' % (src_string),
        R''
    ]
    return output_example

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