#!/usr/bin/env python3

from collections import namedtuple
from urllib import parse, request
import re

def get_alpine_version(tag):
    match tag:
        case "0.3.0" \
            | "0.3.1" \
            | "0.3.2" \
            | "0.3.3" \
            | "0.3.4" \
            | "0.3.5":
            return "3.15.6"
        case _:
            p = re.compile('^0\.[4-9]{1,}.*$')
            p = re.compile('^([0-9]{1,})\.([0-9]{1,})\.([0-9]{1,})$')
            m = p.match(tag)
            if m is not None:
                major_v = int(m.group(1))
                minor_v = int(m.group(2))
                # patch_v = int(m.group(3))
                if major_v == 0 and minor_v > 3:
                    return "3.16.2"
                return None
            return None

def get_alpine_pkg_string(tag, pkg):
    p = re.compile(
        '.* pkgname=([^ ]{1,}).* pkgver=([^ ]{1,}).* pkgrel=([^ ]{1,}) .*'
    )
    match tag:
        case "3.15.6" | "3.16.2":
            url = 'https://raw.githubusercontent.com/alpinelinux/aports/v' + \
            tag + '/main/' + pkg + '/APKBUILD'
            with request.urlopen(url) as response:
                pkg_data = response.read()\
                                    .decode('UTF-8')\
                                    .replace('\n', ' ')
                m = p.search(pkg_data)
                if m is not None:
                    pkg_name = m.group(1)
                    pkg_ver = m.group(2)
                    pkg_rel = m.group(3)
                    if pkg_name == pkg:
                        return f'{pkg_name}={pkg_ver}-r{pkg_rel}'
                else:
                    return None
        case _:
            return None

def get_granular_dependency_version(tag, dep):
    match dep:
        case "binaryen":
            match tag:
                case "0.3.0" | "0.3.1" | "0.3.2":
                    return "104"
                case "0.3.3" | "0.3.4" | "0.3.5":
                    return "105"
                case "0.4.0-beta.1":
                    return "108"
                case "0.4.0-beta.2" \
                    | "0.4.0-beta.3" \
                    | "0.4.0-beta.4" \
                    | "0.4.0-beta.5" \
                    | "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "109"
                case _:
                    return None
        case "bonnie":
            return "0.3.2"
        case "browser-sync":
            match tag:
                case "0.3.0" | "0.3.1" | "0.3.2" | "0.3.3":
                    return "2.27.7"
                case "0.3.4":
                    return "2.27.9"
                case "0.3.5" \
                    | "0.4.0-beta.1" \
                    | "0.4.0-beta.2" \
                    | "0.4.0-beta.3" \
                    | "0.4.0-beta.4" \
                    | "0.4.0-beta.5" \
                    | "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "2.27.10"
                case _:
                    return None
        case "concurrently":
            match tag:
                case "0.3.0":
                    return "6.5.1"
                case "0.3.1" | "0.3.2" | "0.3.3":
                    return "7.0.0"
                case "0.3.4" | "0.3.5":
                    return "7.1.0"
                case "0.4.0-beta.1":
                    return "7.2.1"
                case "0.4.0-beta.2":
                    return "7.2.2"
                case "0.4.0-beta.3" \
                    | "0.4.0-beta.4" \
                    | "0.4.0-beta.5" \
                    | "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "7.3.0"
                case _:
                    return None
        case "esbuild":
            match tag:
                case "0.3.0":
                    return "0.14.6"
                case "0.3.1":
                    return "0.14.10"
                case "0.3.2":
                    return "0.14.11"
                case "0.3.3":
                    return "0.14.21"
                case "0.3.4" | "0.3.5":
                    return "0.14.36"
                case "0.4.0-beta.1":
                    return "0.14.42"
                case "0.4.0-beta.2":
                    return "0.14.47"
                case "0.4.0-beta.3":
                    return "0.14.48"
                case "0.4.0-beta.4" | "0.4.0-beta.5":
                    return "0.14.49"
                case "0.4.0-beta.6" | "0.4.0-beta.7":
                    return "0.15.3"
                case _:
                    return None
        case "node":
            match tag:
                case "0.3.0" | "0.3.1":
                    return "17.3.0"
                case "0.3.2":
                    return "17.3.1"
                case "0.3.3":
                    return "17.5.0"
                case "0.3.4" | "0.3.5":
                    return "18.0.0"
                case "0.4.0-beta.1":
                    return "18.2.0"
                case "0.4.0-beta.2" | "0.4.0-beta.3":
                    return "18.4.0"
                case "0.4.0-beta.4" | "0.4.0-beta.5":
                    return "18.6.0"
                case "0.4.0-beta.6" | "0.4.0-beta.7":
                    return "18.7.0"
                case _:
                    return None
        case "npm":
            match tag:
                case "0.3.0" | "0.3.1." | "0.3.2":
                    return "8.3.0"
                case "0.3.3":
                    return "8.4.1"
                case "0.3.4" | "0.3.5":
                    return "8.6.0"
                case "0.4.0-beta.1":
                    return "8.9.0"
                case "0.4.0-beta.2" | "0.4.0-beta.3":
                    return "8.12.1"
                case "0.4.0-beta.4" | "0.4.0-beta.5":
                    return "8.13.2"
                case "0.4.0-beta.6" | "0.4.0-beta.7":
                    return "8.15.0"
                case _:
                    return None
        case "nvm":
            return "0.39.1"
        case "perseus-size-opt":
            match tag:
                case "0.3.0" | "0.3.1" | "0.3.2" | "0.3.3":
                    return "0.1.7"
                case "0.3.4":
                    return "0.1.8"
                case "0.3.5":
                    return "0.1.9"
                case _:
                    return None
        case "rustup":
            match tag:
                case "0.3.0" \
                    | "0.3.1" \
                    | "0.3.2" \
                    | "0.3.3" \
                    | "0.3.4" \
                    | "0.3.5" \
                    | "0.4.0-beta.1" \
                    | "0.4.0-beta.2" \
                    | "0.4.0-beta.3":
                    return "1.24.3"
                case "0.4.0-beta.4" \
                    | "0.4.0-beta.5" \
                    | "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "1.25.1"
                case _:
                    return None
        case "rust":
            match tag:
                case "0.3.0" | "0.3.1" | "0.3.2":
                    return "1.57.0"
                case "0.3.3":
                    return "1.58.1"
                case "0.3.4" | "0.3.5":
                    return "1.60.0"
                case "0.4.0-beta.1" | "0.4.0-beta.2":
                    return "1.61.0"
                case "0.4.0-beta.3" | "0.4.0-beta.4" | "0.4.0-beta.5":
                    return "1.62.0"
                case "0.4.0-beta.6" | "0.4.0-beta.7":
                    return "1.63.0"
                case _:
                    return None
        case "serve":
            match tag:
                case "0.3.0" \
                    | "0.3.1" \
                    | "0.3.2" \
                    | "0.3.3" \
                    | "0.3.4" \
                    | "0.3.5" \
                    | "0.4.0-beta.1" \
                    | "0.4.0-beta.2" \
                    | "0.4.0-beta.3":
                    return "13.0.2"
                case "0.4.0-beta.4":
                    return "13.0.4"
                case "0.4.0-beta.5" \
                    | "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "14.0.1"
                case _:
                    return None
        case "tailwindcss":
            match tag:
                case "0.3.0":
                    return "3.0.7"
                case "0.3.1":
                    return "3.0.8"
                case "0.3.2":
                    return "3.0.12"
                case "0.3.3":
                    return "3.0.22"
                case "0.3.4" \
                    | "0.3.5" \
                    | "0.4.0-beta.1":
                    return "3.0.24"
                case "0.4.0-beta.2" \
                    | "0.4.0-beta.3":
                    return "3.1.4"
                case "0.4.0-beta.4" \
                    | "0.4.0-beta.5":
                    return "3.1.6"
                case "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "3.1.8"
                case _:
                    return None
        case "wasm-pack":
            match tag:
                case "0.3.0" \
                    | "0.3.1" \
                    | "0.3.2" \
                    | "0.3.3" \
                    | "0.3.4" \
                    | "0.3.5" \
                    | "0.4.0-beta.1":
                    return "0.10.2"
                case "0.4.0-beta.2" \
                    | "0.4.0-beta.3" \
                    | "0.4.0-beta.4" \
                    | "0.4.0-beta.5" \
                    | "0.4.0-beta.6" \
                    | "0.4.0-beta.7":
                    return "0.10.3"
                case _:
                    return None
        case _:
            return None

perseus_version = "0.3.0"

alpine_version = get_alpine_version(perseus_version)

rustup_target = "wasm32-unknown-unknown"

PerseusRelease = namedtuple(
    "PerseusRelease",
    [
        "tag",
        "os"
    ]
)

OperatingSystem = namedtuple(
    "OperatingSystem",
    [
        "name",
        "version",
        "dep"
    ]
)

OSTarget = namedtuple(
    "OSTarget",
    [
        "bash",
        "pkg",
        "rust"
    ]
)

Dependency = namedtuple(
    "Dependency",
    [
        "name",
        "version"
    ]
)

perseus_deps = [
    PerseusRelease(
        "0.3.0",
        OperatingSystem(
            "alpine",
            "3.15.6",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "104"),
                Dependency("browser-sync",      "2.27.7"),
                Dependency("concurrently",      "6.5.1"),
                Dependency("esbuild",           "0.14.6"),
                Dependency("git",               "2.34.1"),
                Dependency("linux-headers",     "5.10.41-r0"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.2-r7"),
                Dependency("node",              "17.3.0"),
                Dependency("npm",               "8.3.0"),
                Dependency("openrc",            "0.44.7-r5"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.0-r1"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r0"),
                Dependency("rust",              "1.57.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.7"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.3.1",
        OperatingSystem(
            "alpine",
            "3.15.6",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "104"),
                Dependency("browser-sync",      "2.27.7"),
                Dependency("concurrently",      "7.0.0"),
                Dependency("esbuild",           "0.14.10"),
                Dependency("git",               "2.34.1"),
                Dependency("linux-headers",     "5.10.41-r0"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.2-r7"),
                Dependency("node",              "17.3.0"),
                Dependency("npm",               "8.3.0"),
                Dependency("openrc",            "0.44.7-r5"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.0-r1"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r0"),
                Dependency("rust",              "1.57.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.8"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.3.2",
        OperatingSystem(
            "alpine",
            "3.15.6",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "104"),
                Dependency("browser-sync",      "2.27.7"),
                Dependency("concurrently",      "7.0.0"),
                Dependency("esbuild",           "0.14.11"),
                Dependency("git",               "2.34.1"),
                Dependency("linux-headers",     "5.10.41-r0"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.2-r7"),
                Dependency("node",              "17.3.1"),
                Dependency("npm",               "8.3.0"),
                Dependency("openrc",            "0.44.7-r5"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.0-r1"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r0"),
                Dependency("rust",              "1.57.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.12"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.3.3",
        OperatingSystem(
            "alpine",
            "3.15.6",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "105"),
                Dependency("browser-sync",      "2.27.7"),
                Dependency("concurrently",      "7.0.0"),
                Dependency("esbuild",           "0.14.21"),
                Dependency("git",               "2.35.1"),
                Dependency("linux-headers",     "5.10.41-r0"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.2-r7"),
                Dependency("node",              "17.5.0"),
                Dependency("npm",               "8.4.1"),
                Dependency("openrc",            "0.44.7-r5"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.0-r1"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r0"),
                Dependency("rust",              "1.58.1"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.22"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.3.4",
        OperatingSystem(
            "alpine",
            "3.15.6",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "105"),
                Dependency("browser-sync",      "2.27.9"),
                Dependency("concurrently",      "7.1.0"),
                Dependency("esbuild",           "0.14.36"),
                Dependency("git",               "2.36.0"),
                Dependency("linux-headers",     "5.10.41-r0"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.2-r7"),
                Dependency("node",              "18.0.0"),
                Dependency("npm",               "8.6.0"),
                Dependency("openrc",            "0.44.7-r5"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.0-r1"),
                Dependency("perseus-size-opt",  "0.1.8"),
                Dependency("pkgconf",           "1.8.0-r0"),
                Dependency("rust",              "1.60.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.24"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.3.5",
        OperatingSystem(
            "alpine",
            "3.15.6",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "105"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.1.0"),
                Dependency("esbuild",           "0.14.36"),
                Dependency("git",               "2.36.0"),
                Dependency("linux-headers",     "5.10.41-r0"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.2-r7"),
                Dependency("node",              "18.0.0"),
                Dependency("npm",               "8.6.0"),
                Dependency("openrc",            "0.44.7-r5"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.0-r1"),
                Dependency("perseus-size-opt",  "0.1.9"),
                Dependency("pkgconf",           "1.8.0-r0"),
                Dependency("rust",              "1.60.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.24"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.1",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "108"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.2.1"),
                Dependency("esbuild",           "0.14.42"),
                Dependency("git",               "2.36.1"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.2.0"),
                Dependency("npm",               "8.9.0"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.61.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.0.24"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.2",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "109"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.2.2"),
                Dependency("esbuild",           "0.14.47"),
                Dependency("git",               "2.36.2"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.4.0"),
                Dependency("npm",               "8.12.1"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.61.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.3"),
                Dependency("tailwindcss",       "3.1.4"),
                Dependency("wasm-pack",         "0.10.2"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.3",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "109"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.3.0"),
                Dependency("esbuild",           "0.14.48"),
                Dependency("git",               "2.37.1"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.4.0"),
                Dependency("npm",               "8.12.1"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.62.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.1.4"),
                Dependency("wasm-pack",         "0.10.3"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.4",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "109"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.3.0"),
                Dependency("esbuild",           "0.14.49"),
                Dependency("git",               "2.37.1"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.6.0"),
                Dependency("npm",               "8.13.2"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.62.0"),
                Dependency("rustup",            "1.24.3"),
                Dependency("serve",             "13.0.2"),
                Dependency("tailwindcss",       "3.1.6"),
                Dependency("wasm-pack",         "0.10.3"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.5",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "109"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.3.0"),
                Dependency("esbuild",           "0.14.49"),
                Dependency("git",               "2.37.1"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.6.0"),
                Dependency("npm",               "8.13.2"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.62.0"),
                Dependency("rustup",            "1.25.1"),
                Dependency("serve",             "13.0.4"),
                Dependency("tailwindcss",       "3.1.6"),
                Dependency("wasm-pack",         "0.10.3"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.6",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "109"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.3.0"),
                Dependency("esbuild",           "0.15.3"),
                Dependency("git",               "2.37.2"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.7.0"),
                Dependency("npm",               "8.15.0"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.63.0"),
                Dependency("rustup",            "1.25.1"),
                Dependency("serve",             "14.0.1"),
                Dependency("tailwindcss",       "3.1.8"),
                Dependency("wasm-pack",         "0.10.3"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
    PerseusRelease(
        "0.4.0-beta.7",
        OperatingSystem(
            "alpine",
            "3.16.2",
            [
                Dependency("alpine-sdk",        "1.0-r1"),
                Dependency("binaryen",          "109"),
                Dependency("browser-sync",      "2.27.10"),
                Dependency("concurrently",      "7.3.0"),
                Dependency("esbuild",           "0.15.3"),
                Dependency("git",               "2.37.2"),
                Dependency("linux-headers",     "5.16.7-r1"),
                Dependency("make",              "4.3-r0"),
                Dependency("musl-dev",          "1.2.3-r0"),
                Dependency("node",              "18.7.0"),
                Dependency("npm",               "8.15.0"),
                Dependency("openrc",            "0.44.10-r7"),
                Dependency("openssl",           "1.1.1q"),
                Dependency("perl",              "5.34.1-r0"),
                Dependency("perseus-size-opt",  "0.1.7"),
                Dependency("pkgconf",           "1.8.0-r1"),
                Dependency("rust",              "1.63.0"),
                Dependency("rustup",            "1.25.1"),
                Dependency("serve",             "14.0.1"),
                Dependency("tailwindcss",       "3.1.8"),
                Dependency("wasm-pack",         "0.10.3"),
                Dependency("zlib-dev",          "1.2.12-r3"),
            ],
        ),
    ),
]