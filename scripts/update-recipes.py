#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import copy
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

from typing import Any, Dict, List, Optional, Tuple

import requests

from ruamel.yaml import YAML

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or None

GITHUB_LATEST_RELEASE = "https://api.github.com/repos/{}/{}/releases/latest"


class Error(Exception):
    """Base class for errors."""


def latest_release(repository: str, apk_patterns: List[str], *,
                   verbose: bool = False) -> Tuple[str, Dict[str, str]]:
    """Get latest release tag & APK URLs."""
    if repository.endswith(".git"):
        repository = repository[:-4]
    url = urllib.parse.urlparse(repository)
    apk_urls = {}
    if url.hostname == "github.com":
        user, repo = url.path.strip("/").split("/")
        data = github_latest_release(user, repo, verbose=verbose)
        tag = data["tag_name"]
        for apk_pattern in apk_patterns:
            for asset in data["assets"]:
                if re.fullmatch(apk_pattern, asset["name"]):
                    apk_urls[apk_pattern] = asset["browser_download_url"]
                    break
    else:
        raise NotImplementedError(f"Unsupported forge: {url.hostname}")
    if not set(apk_urls) == set(apk_patterns):
        raise Error("could not find all APK assets")
    return tag, apk_urls


def latest_tag(repository: str, tag_pattern: str, *, verbose: bool = False) -> str:
    """Get latest tag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "repo")
        clone_cmd = ("git", "clone", "--", repository, repo_dir)
        tags_cmd = ("git", "tag", "--sort=-creatordate")
        if verbose:
            print(f"Cloning {repository!r}...", file=sys.stderr)
        subprocess.run(clone_cmd, check=True)
        proc = subprocess.run(tags_cmd, check=True, capture_output=True, cwd=repo_dir)
        for tag in proc.stdout.decode().splitlines():
            if re.fullmatch(tag_pattern, tag):
                return tag
    raise Error(f"could not find a tag matching pattern {tag_pattern}")


# FIXME: retry, configure timeout
def github_latest_release(user: str, repo: str, *, verbose: bool = False) -> Dict[Any, Any]:
    """Get latest release from GitHub API."""
    url = GITHUB_LATEST_RELEASE.format(user, repo)
    headers = dict(Authorization=f"token {GITHUB_TOKEN}") if GITHUB_TOKEN else {}
    if verbose:
        print(f"Checking {url!r}...", file=sys.stderr)
    with requests.get(url, headers=headers, timeout=60) as response:
        response.raise_for_status()
        return response.json()      # type: ignore[no-any-return]


def load_recipe(recipe_file: str) -> Dict[Any, Any]:
    """Load YAML recipe."""
    with open(recipe_file, encoding="utf-8") as fh:
        yaml = YAML(typ="safe")
        return yaml.load(fh)        # type: ignore[no-any-return]


def save_recipe(recipe_file: str, data: Dict[Any, Any]) -> None:
    """Save YAML recipe."""
    with open(recipe_file, "w", encoding="utf-8") as fh:
        yaml = YAML()
        yaml.explicit_start = True  # type: ignore[assignment,unused-ignore]
        yaml.width = 4096           # type: ignore[assignment,unused-ignore]
        yaml.indent(sequence=4, mapping=2, offset=2)
        yaml.dump(data, fh)


def append_latest_version(recipe: Dict[Any, Any], tag: str,
                          apk_urls: Optional[Dict[str, str]]) -> bool:
    """Add new version to recipe; modifies in-place!"""
    if tag in [v["tag"] for v in recipe["versions"]]:
        return False
    latest_version = copy.deepcopy(recipe["versions"][-1])
    latest_version["tag"] = tag
    if apk_urls:
        for apk in latest_version["apks"]:
            apk_url = apk_urls[apk["apk_pattern"]]
            # only need to replace $$TAG$$ as this must be updates: releases
            if apk_url != apk["apk_url"].replace("$$TAG$$", tag):
                apk["apk_url"] = apk_url
    recipe["versions"].append(latest_version)
    return True


def update_recipes(*recipes: str, verbose: bool = False) -> None:
    """Update recipes."""
    if verbose and GITHUB_TOKEN:
        print("Using $GITHUB_TOKEN.", file=sys.stderr)
    for recipe_file in recipes:
        appid = os.path.splitext(os.path.basename(recipe_file))[0]
        if verbose:
            print(f"Updating {appid!r}...", file=sys.stderr)
        recipe = load_recipe(recipe_file)
        repository = recipe["repository"]
        updates = recipe["updates"]
        if verbose:
            print(f"Updates mode: {updates!r}.", file=sys.stderr)
        if updates == "manual":
            continue
        if updates == "releases":
            apk_patterns = [apk["apk_pattern"] for apk in recipe["versions"][-1]["apks"]]
            tag, apk_urls = latest_release(repository, apk_patterns, verbose=verbose)
            if verbose:
                for apk_url in apk_urls.values():
                    print(f"Found tag {tag!r} with APK URL {apk_url!r}.", file=sys.stderr)
        elif updates.startswith("tags:"):
            tag = latest_tag(repository, updates[5:], verbose=verbose)
            apk_urls = None
            if verbose:
                print(f"Found tag {tag!r}.", file=sys.stderr)
        else:
            raise NotImplementedError(f"Unsupported updates mode: {updates}")
        if append_latest_version(recipe, tag, apk_urls):
            save_recipe(recipe_file, recipe)
        elif verbose:
            print(f"Tag already present: {tag!r}.", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="update recipes")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("recipes", metavar="RECIPE", nargs="*", help="recipe")
    args = parser.parse_args()
    update_recipes(*args.recipes, verbose=args.verbose)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
