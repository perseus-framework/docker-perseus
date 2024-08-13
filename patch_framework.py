#!/usr/bin/env python3

import re

def patch(semver):
    sv_pat = re.compile('([0-9\.]{5,})$')
    sv_match = re.search(
        pattern=sv_pat,
        string=semver
    )
    release = sv_match.group(0)
    if release == '0.3.0':
        # Apply changes to /perseus/packages/perseus/src/lib.rs
        # Apply changes to /perseus/packages/perseus-cli/src/cmd.rs
        # Create path /perseus/examples/fetching
        # Download tarball of v0.3.1 example into created path
        # Create path /perseus/packages/perseus-size-opt
        # Download tarball of perseus-size-opt into created path
        # Remove examples from perseus-size-opt download
        # Scan contents of /perseus/packages/perseus-size-opt/Cargo.toml
        # Record line number of [workspace] in cargo file.
        # Record line number of next ] that appears in cargo file.
        # Delete both lines from the cargo file.
        # Globally replace HOST with PERSEUS_HOST in the files listed below.
        # Globally replace PORT with PERSEUS_PORT in the files listed below.
        #   - /perseus/packages/perseus-cli/src/parse.rs
        #   - /perseus/packages/perseus-cli/src/serve.rs
        # NOTE: The following file may be included in error prior to
        #       preferred use of the fetching example.
        #   - /perseus/examples/basic/.perseus/server/src/main.rs
        pass
    elif release == '0.3.1':
        pass
    elif release == '0.3.2':
        pass
    else:
        pass

# TODO: Populate logic in this script file.
# NOTE: All versions will need to be taken into account.