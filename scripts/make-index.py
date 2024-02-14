#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import json
import os
import sys

from typing import Any, Dict


def load_log(log_file: str) -> Dict[Any, Any]:
    """Load JSON log."""
    with open(log_file, encoding="utf-8") as fh:
        return json.load(fh)    # type: ignore[no-any-return]


def make_index(*log_files: str, verbose: bool = False) -> None:
    """Make JSON index from JSON logs."""
    data: Dict[Any, Any] = {}
    for log_file in log_files:
        appid = os.path.splitext(os.path.basename(log_file))[0]
        if verbose:
            print(f"Procesing {appid!r}...", file=sys.stderr)
        for tag, logs in load_log(log_file)["tags"].items():
            for log in logs:
                sha256 = log["upstream_signed_apk_sha256"]
                if sha256 is None:
                    continue
                if sha256 not in data:
                    data[sha256] = []
                entry = dict(repository=log["recipe"]["repository"])
                for k in ("appid", "version_code", "version_name", "tag",
                          "commit", "timestamp", "reproducible", "error"):
                    entry[k] = log[k]
                data[sha256].append(entry)
    json.dump(data, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="make index")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("logs", metavar="LOG", nargs="*", help="log")
    args = parser.parse_args()
    make_index(*args.logs, verbose=args.verbose)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
