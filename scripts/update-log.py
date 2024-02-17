#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import json
import os
import subprocess
import sys

from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

EXE = sys.executable or "python3"


def recipe_tags(recipe_file: str) -> List[str]:
    """Parse recipe YAML and get tags."""
    with open(recipe_file, encoding="utf-8") as fh:
        yaml = YAML(typ="safe")
        data = yaml.load(fh)
        return [v["tag"] for v in data["versions"]]


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
            if version_code not in log_data["version_codes"]:
                log_data["version_codes"][version_code] = []
            tags = log_data["version_codes"][version_code]
            log_data["version_codes"][version_code] = sorted(set(tags) | set([tag]))
        if sha256 is not None:
            if sha256 not in log_data["sha256"]:
                log_data["sha256"][sha256] = []
            tags = log_data["sha256"][sha256]
            log_data["sha256"][sha256] = sorted(set(tags) | set([tag]))
    return log_data


# FIXME
def update_log(backend: str, *recipes: str, keep_apks: Optional[str] = None,
               verbose: bool = False) -> None:
    """Update log."""
    for recipe_file in recipes:
        appid = os.path.splitext(os.path.basename(recipe_file))[0]
        if verbose:
            print(f"Updating {appid!r}...", file=sys.stderr)
        log_file = os.path.join("logs", f"{appid}.json")
        log = load_log(log_file, appid)
        old_tags = set(log["tags"])
        new_tags = recipe_tags(recipe_file)
        to_build = []
        for tag in new_tags:
            if tag not in old_tags:
                to_build.append(f"{appid}:{tag}")
        if not to_build:
            if verbose:
                print("Nothing to build.", file=sys.stderr)
            continue
        if verbose:
            print(f"Building {to_build!r}...", file=sys.stderr)
        verb = ("--verbose",) if verbose else ()
        keep = ("--keep-apks", keep_apks) if keep_apks else ()
        args = (EXE, os.path.join("scripts", "build.py"), *verb, *keep, "--", backend, *to_build)
        output = subprocess.run(args, check=True, stdout=subprocess.PIPE).stdout.decode()
        builds = json.loads(output)
        save_log(log_file, add_builds(load_log(log_file, appid), builds))


if __name__ == "__main__":
    backends = ("podman", "docker")
    parser = argparse.ArgumentParser(description="update log")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--keep-apks", metavar="DIR", help="save APKs in DIR")
    parser.add_argument("backend", choices=backends, help="backend")
    parser.add_argument("recipes", metavar="RECIPE", nargs="*", help="recipe")
    args = parser.parse_args()
    update_log(args.backend, *args.recipes, keep_apks=args.keep_apks, verbose=args.verbose)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
