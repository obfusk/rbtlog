#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import copy
import os
import sys
import urllib.parse

from typing import Any, Dict, Tuple

import requests

from ruamel.yaml import YAML

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or None

GITHUB_LATEST_RELEASE = "https://api.github.com/repos/{}/{}/releases/latest"


class Error(Exception):
    """Base class for errors."""


def latest_release(recipe: Dict[Any, Any], *, verbose: bool = False) -> Tuple[str, str]:
    """Get latest release tag & APK URL."""
    if (repo := recipe["repository"]).endswith(".git"):
        repo = repo[:-4]
    url = urllib.parse.urlparse(repo)
    apk_url = None
    if url.hostname == "github.com":
        user, repo = url.path.strip("/").split("/")
        data = github_latest_release(user, repo, verbose=verbose)
        tag = data["tag_name"]
        for asset in data["assets"]:
            if asset["name"].endswith(".apk"):
                apk_url = asset["browser_download_url"]
                break
    else:
        raise NotImplementedError(f"Unsupported forge: {url.hostname}")
    if apk_url is None:
        raise Error("could not find APK asset")
    return tag, apk_url


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
        yaml.explicit_start = True  # type: ignore[assignment]
        yaml.width = 4096           # type: ignore[assignment]
        yaml.indent(sequence=4, mapping=2, offset=2)
        yaml.dump(data, fh)


def append_latest_version(recipe: Dict[Any, Any], tag: str, apk_url: str) -> bool:
    """Add new version to recipe; modifies in-place!"""
    if tag in [v["tag"] for v in recipe["versions"]]:
        return False
    latest_version = copy.deepcopy(recipe["versions"][-1])
    latest_version["tag"] = tag
    if apk_url != latest_version["apk_url"].replace("$$TAG$$", tag):
        latest_version["apk_url"] = apk_url
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
        tag, apk_url = latest_release(recipe, verbose=verbose)
        if verbose:
            print(f"Found tag {tag!r} with APK URL {apk_url!r}.", file=sys.stderr)
        if append_latest_version(recipe, tag, apk_url):
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
