#!/usr/bin/env python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import json
import os
import sys

from typing import Any, Dict, List


def load_log(log_file: str, appid: str) -> Dict[Any, Any]:
    """Load JSON log."""
    try:
        with open(log_file, encoding="utf-8") as fh:
            return json.load(fh)    # type: ignore[no-any-return]
    except FileNotFoundError:
        return dict(appid=appid, tags={}, version_codes={}, sha256={})


def save_log(log_file: str, data: Dict[Any, Any]) -> None:
    """Save JSON log,"""
    with open(log_file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


# FIXME
def add_builds(log_data: Dict[Any, Any], builds: List[Dict[Any, Any]]) -> Dict[Any, Any]:
    """Add builds to log; modifies in-place!"""
    for build in builds:
        tag, version_code = build["tag"], build["version_code"]
        sha256 = build["upstream_signed_apk_sha256"]
        if tag not in log_data["tags"]:
            log_data["tags"][tag] = []
        log_data["tags"][tag].append(build)
        if version_code is not None:
            vc = str(version_code)
            if vc not in log_data["version_codes"]:
                log_data["version_codes"][vc] = []
            tags = log_data["version_codes"][vc]
            log_data["version_codes"][vc] = sorted(set(tags) | set([tag]))
        if sha256 is not None:
            if sha256 not in log_data["sha256"]:
                log_data["sha256"][sha256] = []
            tags = log_data["sha256"][sha256]
            log_data["sha256"][sha256] = sorted(set(tags) | set([tag]))
    return log_data


def append_builds(log_file: str) -> None:
    """Append build logs."""
    appid = os.path.splitext(os.path.basename(log_file))[0]
    builds = json.load(sys.stdin)
    save_log(log_file, add_builds(load_log(log_file, appid), builds))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="append builds")
    parser.add_argument("log")
    args = parser.parse_args()
    append_builds(args.log)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
