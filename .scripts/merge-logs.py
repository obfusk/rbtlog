#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import json
import os

from typing import Any, Dict


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


def merge_logs(log_file: str, second_log_file: str, tag: str) -> None:
    """Merge logs."""
    appid = os.path.splitext(os.path.basename(log_file))[0]
    log = load_log(log_file, appid)
    second_log = load_log(second_log_file, appid)
    log["tags"][tag] += second_log["tags"][tag]
    save_log(log_file, log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="merge logs")
    parser.add_argument("log")
    parser.add_argument("second_log")
    parser.add_argument("tag")
    args = parser.parse_args()
    merge_logs(args.log, args.second_log, args.tag)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
