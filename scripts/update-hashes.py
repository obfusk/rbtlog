#!/usr/bin/env python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile

from typing import Any, Dict, List, Optional, Tuple

import requests

from ruamel.yaml import YAML


FILES = {
    "DEX": re.compile(r"classes\d*\.dex"),
    "PROF": "assets/dexopt/baseline.prof",
    "PROFM": "assets/dexopt/baseline.profm",
}
VCSINFO_FILE = "META-INF/version-control-info.textproto"
VCSINFO_REGEX = re.compile(r'revision: "([0-9a-f]{40})"')

REPRO_APK = "obfusk/reproducible-apk-tools"
REPRO_APK_URL = f"https://github.com/{REPRO_APK}.git"


class Error(Exception):
    """Base class for errors."""


@functools.lru_cache(maxsize=None)
def load_versions() -> Dict[Any, Any]:
    """Load versions.json."""
    with open("versions.json", encoding="utf-8") as fh:
        return json.load(fh)        # type: ignore[no-any-return]


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


def download_file(url: str, output: str) -> None:
    """Download file."""
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(output, "wb") as fh:
            for chunk in response.iter_content(chunk_size=4096):
                fh.write(chunk)


def download_file_with_retries(url: str, output: str, *, retries: int = 5) -> None:
    """Download file w/ retries."""
    error: Exception = Error("No retries")
    for i in range(retries):
        if i:
            time.sleep(1)
        try:
            download_file(url, output)
            return
        except requests.RequestException as e:
            error = e
    raise error


def retrieve_apk_hashes(apk_url: str, files: List[str]) -> Tuple[Dict[str, str], Optional[str]]:
    """
    Download upstream APK and get SHA-1 hashes for specified files in APK +
    embedded git commit (if any).
    """
    hashes = {}
    commit = None
    with tempfile.TemporaryDirectory() as tmpdir:
        upstream_apk = os.path.join(tmpdir, "upstream.apk")
        download_file_with_retries(apk_url, upstream_apk)
        with zipfile.ZipFile(upstream_apk) as zf:
            if VCSINFO_FILE in zf.namelist():
                if m := VCSINFO_REGEX.search(zf.read(VCSINFO_FILE).decode()):
                    commit = m.group(1)
            for file in files:
                sha = hashlib.sha1()
                with zf.open(file) as fh:
                    while data := fh.read(4096):
                        sha.update(data)
                hashes[file] = sha.hexdigest()
    return hashes, commit


def url_with_replacements(apk_url: str, tag: str, tag_pattern: Optional[str]) -> str:
    """URL with $$TAG$$ $$TAG:1$$ etc. replaced."""
    url = apk_url.replace("$$TAG$$", tag)
    if tag_pattern and (m := re.fullmatch(tag_pattern, tag)):
        for i, group in enumerate(m.groups("")):
            url = url.replace(f"$$TAG:{i + 1}$$", group)
    return url


def tag_to_commit(repository: str, tag: str) -> str:
    r"""
    Get commit hash for tag.

    >>> tag_to_commit("https://github.com/CatimaLoyalty/Android.git", "v2.27.0")
    '84c343e41f4a09ee3fe6ee0924a3446ae325c4b7'
    >>> tag_to_commit("https://github.com/threema-ch/threema-android.git", "5.2.3")
    '14388d856b28bdbe1417d0f92fed09567263c36e'

    """
    args = ("git", "ls-remote", "--tags", "--", repository)
    output = subprocess.run(args, check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT).stdout.decode()
    refs = {}
    for line in output.splitlines():
        commit, ref = line.split("\t", 1)
        refs[ref] = commit
    tag_ref = f"refs/tags/{tag}"
    peeled_ref = tag_ref + "^{}"
    if peeled_ref in refs:
        return refs[peeled_ref]
    if tag_ref in refs:
        return refs[tag_ref]
    raise Error(f"Tag not found: {tag}")


# FIXME: more no-update-* labels?!
def update_recipe_hashes(data: Dict[Any, Any], repo: str, tag: str, tag_pattern: Optional[str],
                         *, verbose: bool = False) -> bool:
    """Update recipe hashes."""
    labels = data.get("labels", [])
    modified = False
    for vsn in data["versions"]:
        if vsn["tag"] == tag:
            for apk in vsn["apks"]:
                apk_url = url_with_replacements(apk["apk_url"], tag, tag_pattern)
                lines_files = find_file_hashes(apk)
                hashes, apk_commit = retrieve_apk_hashes(apk_url, [p for _, p in lines_files])
                tag_commit = tag_to_commit(repo, tag)
                for i, path in lines_files:
                    update_file_hash(apk, i, path, hashes)
                    modified = True
                    if verbose:
                        print(f"SHA-1 {path!r}: {hashes[path]!r}.", file=sys.stderr)
                if update_commit_hash(apk, apk_commit, tag_commit):
                    modified = True
                    if verbose:
                        if apk_commit:
                            print(f"Reset: {apk_commit!r}, tag: {tag_commit!r}.", file=sys.stderr)
                        else:
                            print("Removed reset (no embedded commit hash).", file=sys.stderr)
                if "no-update-cmdline-tools" not in labels and (vsn := update_cmdline_tools(apk)):
                    modified = True
                    if verbose:
                        print(f"Updated cmdline_tools to {vsn}.", file=sys.stderr)
                if "no-update-nodejs-lts" not in labels and (vsn := update_nodejs_lts(apk)):
                    modified = True
                    if verbose:
                        print(f"Updated node.js LTS to {vsn}.", file=sys.stderr)
                if "no-update-repro-apk" not in labels and (vsn := update_repro_apk(apk)):
                    modified = True
                    if verbose:
                        print(f"Updated repro-apk to {vsn}.", file=sys.stderr)
    return modified


def find_file_hashes(apk: Dict[Any, Any]) -> List[Tuple[int, str]]:
    """Find (line_index, apk_file_path) for .dex/.prof/.profm hashes in recipe."""
    files = []
    for i in range(len(apk["build"]) - 1):
        l1, l2 = apk["build"][i], apk["build"][i + 1]
        for prefix, path in FILES.items():
            p1, p2 = f"{prefix}_FILE=", f"{prefix}_SHA1="
            if not (l1.startswith(p1) and l2.startswith(p2)):
                continue
            filename = l1.rsplit("/", 1)[-1]
            if isinstance(path, re.Pattern) and path.fullmatch(filename):
                files.append((i + 1, filename))
            elif isinstance(path, str) and path.rsplit("/", 1)[-1] == filename:
                files.append((i + 1, path))
    return files


def update_file_hash(apk: Dict[Any, Any], i: int, path: str, hashes: Dict[str, str]) -> None:
    """Update file hash."""
    prefix = apk["build"][i].split("=", 1)[0]
    apk["build"][i] = f"{prefix}={hashes[path]}"


def update_commit_hash(apk: Dict[Any, Any], apk_commit: Optional[str], tag_commit: str) -> bool:
    """Update 'git reset --soft' (or fix-files) for embedded commit hash mismatch."""
    reset, checkout = "git reset --soft", "git checkout"
    cd = False
    for i in range(len(apk["build"])):
        line = apk["build"][i]
        if not cd and (line.startswith(reset) or line.startswith(checkout)):
            if apk_commit and tag_commit != apk_commit:
                apk["build"][i] = f"{reset} {apk_commit}"
            else:
                apk["build"].pop(i)
            return True
        if VCSINFO_FILE in line and "fix-files" in line:
            if apk_commit and tag_commit != apk_commit:
                apk["build"][i] = re.sub(
                    r"sed s/[0-9a-f]{40}/[0-9a-f]{40}/",
                    f"sed s/{tag_commit}/{apk_commit}/", line)
            else:
                apk["build"].pop(i)
            return True
        if line.startswith("cd ") or line.startswith("pushd "):
            cd = True
    if apk_commit and tag_commit != apk_commit:
        apk["build"].insert(0, f"{reset} {apk_commit}")
        return True
    return False


def update_cmdline_tools(apk: Dict[Any, Any]) -> Optional[str]:
    """Update cmdline_tools to use latest version."""
    latest = load_versions()["cmdline_tools"]
    if apk["provisioning"]["cmdline_tools"] != latest:
        apk["provisioning"]["cmdline_tools"] = latest
        return latest["version"]    # type: ignore[no-any-return]
    return None


def update_nodejs_lts(apk: Dict[Any, Any]) -> Optional[str]:
    """Update node.js LTS download to use latest version."""
    lts_zip_txz = re.compile(r"nodejs-lts\.(zip|tar\.xz|txz)")  # .zip by mistake
    nodejs = None
    for i in range(len(apk["build"])):
        line = apk["build"][i]
        if line.startswith("wget") and lts_zip_txz.search(line):
            nodejs = load_versions()["nodejs-lts"]
            apk["build"][i] = re.sub(r"https://nodejs\.org/\S*\.tar\.xz", nodejs["url"], line)
            if line == apk["build"][i]:
                return None
        if nodejs and line.startswith("sha256sum") and lts_zip_txz.search(line):
            apk["build"][i] = re.sub(r"[0-9a-f]{64}", nodejs["sha256"], line)
        if nodejs and line.startswith("export") and "PATH=" in line:
            apk["build"][i] = re.sub(
                r"node-v[\d.]+-linux-x64/bin",
                f"node-{nodejs['version']}-linux-x64/bin", line)
    return nodejs["version"] if nodejs else None


def update_repro_apk(apk: Dict[Any, Any]) -> Optional[str]:
    """Update 'git clone -b vX.Y.Z REPRO_APK_URL' to use latest version."""
    for i in range(len(apk["build"])):
        line = apk["build"][i]
        if line.startswith("git clone") and REPRO_APK_URL in line:
            version = load_versions()["repro-apk"]["tag"]
            apk["build"][i] = re.sub(r" -b v[\d.]+ ", f" -b {version} ", line)
            return version if line != apk["build"][i] else None
    return None


def update_hashes(recipe_file: str, tag: str, *, verbose: bool = False) -> None:
    """Update hashes in build recipe."""
    recipe = load_recipe(recipe_file)
    updates = recipe["updates"]
    tag_pattern = updates.replace("tags:", "", 1) if updates.startswith("tags:") else None
    if update_recipe_hashes(recipe, recipe["repository"], tag, tag_pattern, verbose=verbose):
        save_recipe(recipe_file, recipe)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="update hashes")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("recipe", metavar="RECIPE")
    parser.add_argument("tag", metavar="TAG")
    args = parser.parse_args()
    update_hashes(args.recipe, args.tag, verbose=args.verbose)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
