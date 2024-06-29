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

CODEBERG_DOT_ORG = "codeberg.org"
GITHUB_DOT_COM = "github.com"
GITLAB_DOT_COM = "gitlab.com"

# host, namespace, project
GITEA_RELEASE = "https://{}/api/v1/repos/{}/{}/releases/latest"
# namespace, project
GITHUB_LATEST_RELEASE = "https://api.github.com/repos/{}/{}/releases/latest"
# host, namespace, project
GITLAB_LATEST_RELEASE = "https://{}/api/v4/projects/{}%2F{}/releases/permalink/latest"

# host, namespace, project, upload
GITLAB_UPLOAD = "https://{}/{}/{}/uploads/{}"
# hash/filename
GITLAB_UPLOAD_RX = re.compile(r"\(/uploads/([0-9a-f]{32}/[^/)]+)\)")


class Error(Exception):
    """Base class for errors."""


def latest_release(repository: str, apk_patterns: List[str], *,
                   verbose: bool = False) -> Tuple[str, Dict[str, str]]:
    """Get latest release tag & APK URLs."""
    if repository.endswith(".git"):
        repository = repository[:-4]
    url = urllib.parse.urlparse(repository)
    if url.hostname == CODEBERG_DOT_ORG:
        tag, apk_urls = latest_release_gitea(url, apk_patterns, verbose=verbose)
    elif url.hostname == GITHUB_DOT_COM:
        tag, apk_urls = latest_release_github(url, apk_patterns, verbose=verbose)
    elif url.hostname == GITLAB_DOT_COM:
        tag, apk_urls = latest_release_gitlab(url, apk_patterns, verbose=verbose)
    else:
        raise NotImplementedError(f"Unsupported forge: {url.hostname}")
    if not set(apk_urls) == set(apk_patterns):
        raise Error(f"could not find all APK assets for tag {tag!r}")
    return tag, apk_urls


# FIXME: self-hosted, gitea vs forgejo
def latest_release_gitea(url: urllib.parse.ParseResult, apk_patterns: List[str], *,
                         verbose: bool = False) -> Tuple[str, Dict[str, str]]:
    """Get latest release tag & APK URLs from Gitea/Forgejo."""
    namespace, project = url.path.strip("/").split("/")
    assert url.hostname is not None
    data = gitea_latest_release(url.hostname, namespace, project, verbose=verbose)
    tag = data["tag_name"]
    apk_urls = {}
    for apk_pattern in apk_patterns:
        for asset in data["assets"]:
            if re.fullmatch(apk_pattern, asset["name"]):
                apk_urls[apk_pattern] = asset["browser_download_url"]
                break
    return tag, apk_urls


def latest_release_github(url: urllib.parse.ParseResult, apk_patterns: List[str], *,
                          verbose: bool = False) -> Tuple[str, Dict[str, str]]:
    """Get latest release tag & APK URLs from GitHub."""
    namespace, project = url.path.strip("/").split("/")
    data = github_latest_release(namespace, project, verbose=verbose)
    tag = data["tag_name"]
    apk_urls = {}
    for apk_pattern in apk_patterns:
        for asset in data["assets"]:
            if re.fullmatch(apk_pattern, asset["name"]):
                apk_urls[apk_pattern] = asset["browser_download_url"]
                break
    return tag, apk_urls


# FIXME: self-hosted
def latest_release_gitlab(url: urllib.parse.ParseResult, apk_patterns: List[str], *,
                          verbose: bool = False) -> Tuple[str, Dict[str, str]]:
    """Get latest release tag & APK URLs from GitLab."""
    namespace, project = url.path.strip("/").split("/")
    assert url.hostname is not None
    data = gitlab_latest_release(url.hostname, namespace, project, verbose=verbose)
    tag = data["tag_name"]
    apk_urls = {}
    for apk_pattern in apk_patterns:
        for asset in data["assets"]["links"]:
            if re.fullmatch(apk_pattern, asset["name"]):
                apk_urls[apk_pattern] = asset["direct_asset_url"]
                break
            asset_url = urllib.parse.urlparse(asset["direct_asset_url"])
            if re.fullmatch(apk_pattern, asset_url.path.rsplit("/", 1)[-1]):
                apk_urls[apk_pattern] = asset["direct_asset_url"]
                break
        if apk_pattern in apk_urls:
            continue
        for upload in GITLAB_UPLOAD_RX.findall(data["description"]):
            if re.fullmatch(apk_pattern, upload.rsplit("/", 1)[-1]):
                apk_urls[apk_pattern] = GITLAB_UPLOAD.format(url.hostname, namespace, project, upload)
                break
    return tag, apk_urls


def latest_tag(repository: str, tag_pattern: str, *, verbose: bool = False) -> str:
    """Get latest tag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "repo")
        clone_cmd = ("git", "clone", "--", repository, repo_dir)
        tags_cmd = ("git", "tag", "--sort=-version:refname", "--sort=-creatordate")
        if verbose:
            print(f"Cloning {repository!r}...", file=sys.stderr)
        subprocess.run(clone_cmd, check=True)
        proc = subprocess.run(tags_cmd, check=True, capture_output=True, cwd=repo_dir)
        for tag in proc.stdout.decode().splitlines():
            if re.fullmatch(tag_pattern, tag):
                return tag
    raise Error(f"could not find a tag matching pattern {tag_pattern}")


# FIXME: retry, configure timeout, gitea vs forgejo
def gitea_latest_release(host: str, namespace: str, project: str, *,
                         verbose: bool = False) -> Dict[Any, Any]:
    """Get latest release from Gitea/Forgejo API."""
    url = GITEA_RELEASE.format(host, namespace, project)
    if verbose:
        print(f"Checking {url!r}...", file=sys.stderr)
    with requests.get(url, timeout=60) as response:
        response.raise_for_status()
        return response.json()      # type: ignore[no-any-return]


# FIXME: retry, configure timeout
def github_latest_release(namespace: str, project: str, *, verbose: bool = False) -> Dict[Any, Any]:
    """Get latest release from GitHub API."""
    url = GITHUB_LATEST_RELEASE.format(namespace, project)
    headers = dict(Authorization=f"token {GITHUB_TOKEN}") if GITHUB_TOKEN else {}
    if verbose:
        print(f"Checking {url!r}...", file=sys.stderr)
    with requests.get(url, headers=headers, timeout=60) as response:
        response.raise_for_status()
        return response.json()      # type: ignore[no-any-return]


# FIXME: retry, configure timeout, token (!?)
def gitlab_latest_release(host: str, namespace: str, project: str, *,
                          verbose: bool = False) -> Dict[Any, Any]:
    """Get latest release from GitLab API."""
    url = GITLAB_LATEST_RELEASE.format(host, namespace, project)
    if verbose:
        print(f"Checking {url!r}...", file=sys.stderr)
    with requests.get(url, timeout=60) as response:
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


def update_recipes(*recipes: str, continue_on_errors: bool = False, verbose: bool = False) -> bool:
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
        if checkonly := updates.startswith("checkonly:"):
            updates = updates.replace("checkonly:", "", 1)
        try:
            if updates == "releases":
                apk_patterns = [apk["apk_pattern"] for apk in recipe["versions"][-1]["apks"]]
                tag, apk_urls = latest_release(repository, apk_patterns, verbose=verbose)
                if verbose:
                    for apk_url in apk_urls.values():
                        print(f"Found tag {tag!r} with APK URL {apk_url!r}.", file=sys.stderr)
            elif updates.startswith("tags:"):
                tag_pattern = updates.replace("tags:", "", 1)
                tag = latest_tag(repository, tag_pattern, verbose=verbose)
                apk_urls = None
                if verbose:
                    print(f"Found tag {tag!r}.", file=sys.stderr)
            else:
                raise NotImplementedError(f"Unsupported updates mode: {updates}")
            if append_latest_version(recipe, tag, apk_urls):
                if checkonly:
                    print(f"Update available for {appid!r}: {tag!r}.", file=sys.stderr)
                else:
                    save_recipe(recipe_file, recipe)
                    print(f"Updated {appid!r} to {tag!r}.", file=sys.stderr)
            elif verbose:
                print(f"Tag already present: {tag!r}.", file=sys.stderr)
        except (subprocess.CalledProcessError, requests.RequestException, Error) as e:
            print(f"Error updating {appid!r}: {e}", file=sys.stderr)
            if not continue_on_errors:
                return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="update recipes")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--continue-on-errors", action="store_true", help="continue on errors")
    parser.add_argument("recipes", metavar="RECIPE", nargs="*", help="recipe")
    args = parser.parse_args()
    if not update_recipes(*args.recipes, continue_on_errors=args.continue_on_errors, verbose=args.verbose):
        sys.exit(1)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
