#!/usr/bin/env python3

import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def get_live_os_string(dist):
    match dist:
        case 'alpine':
            url = 'https://github.com/alpinelinux/aports/tags'
            a_open = '.* <a href="/alpinelinux/aports/releases/tag/'
            a_pat = '[v]{1}([0-9]{1,}[\.]{1}[0-9]{1,}[\.]{1}[0-9]{1,})'
            a_close = '"> .*'
        case 'centos':
            url = 'https://mirrors.mit.edu/centos/'
            a_open = '.* <a href="[^ ]{1,}">'
            a_pat = '([0-9\.]{1,})'
            a_close = '/</a> .*'
        case 'debian':
            url = 'https://mirrors.mit.edu/debian/dists/'
            a_open = '.* <a href="[^ ]{1,}">'
            a_pat = 'Debian([0-9\.]{1,})'
            a_close = '/</a> .*'
        case 'fedora':
            url = 'https://mirrors.mit.edu/fedora/linux/releases/'
            a_open = '.* <a href="[^ ]{1,}">'
            a_pat = '([0-9]{1,})'
            a_close = '/</a> .*'
        case 'ubuntu':
            url = 'https://mirrors.mit.edu/ubuntu-releases/'
            a_open = '.* <a href="[^ ]{1,}">'
            a_pat = '([0-9\.]{1,})'
            a_close = '/</a> .*'
        case _:
            return None
    req = Request(url)
    try:
        res = urlopen(req)
    except HTTPError as e:
        print(e.code)
    except URLError as e:
        print(e.reason)
    else:
        tag_data = res.read() \
                    .decode('UTF-8') \
                    .replace('\n', '')
        p = re.compile(f'{a_open}{a_pat}{a_close}')
        i = p.finditer(tag_data)
        for m in i:
            print(m)