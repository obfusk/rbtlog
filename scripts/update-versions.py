#!/usr/bin/env python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import zipfile

from typing import Any, Dict, Optional

import requests


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or None

CMDLINE_TOOLS_PAGE = "https://developer.android.com/studio"
CMDLINE_TOOLS_RX = re.compile(r"https://dl\.google\.com/android/repository/commandlinetools-linux-\d+_latest\.zip")

NODEJS_LTS_PAGE = "https://nodejs.org/en/download/prebuilt-binaries"
NODEJS_LTS_RX = re.compile(r"https://nodejs\.org/dist/(v[\d.]+)/node-(\1).tar.gz")
NODEJS_LTS_LINUX_X64_XZ = "https://nodejs.org/dist/{0}/node-{0}-linux-x64.tar.xz"
NODEJS_SHA256SUMS = "https://nodejs.org/dist/{}/SHASUMS256.txt"

REPRO_APK = "obfusk/reproducible-apk-tools"
REPRO_APK_URL = f"https://github.com/{REPRO_APK}.git"
REPRO_APK_LATEST = f"https://api.github.com/repos/{REPRO_APK}/releases/latest"


class Error(Exception):
    """Base class for errors."""


def load_versions() -> Dict[Any, Any]:
    """Load versions.json."""
    with open("versions.json", encoding="utf-8") as fh:
        return json.load(fh)        # type: ignore[no-any-return]


def save_versions(data: Dict[Any, Any]) -> None:
    """Save versions.json."""
    with open("versions.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def latest_cmdline_tools(current: Dict[Any, Any]) -> Optional[Dict[Any, Any]]:
    """Get latest cmdline_tools from CMDLINE_TOOLS_PAGE."""
    with requests.get(CMDLINE_TOOLS_PAGE, timeout=60) as response:
        response.raise_for_status()
        if m := CMDLINE_TOOLS_RX.search(response.text):
            if (url := m[0]) == current["url"]:
                return None
            with tempfile.TemporaryDirectory() as tmpdir:
                cmdline_tools_zip = os.path.join(tmpdir, "commandlinetools-linux.zip")
                sha256 = download_file_with_retries(url, cmdline_tools_zip)
                version = _cmdline_tools_version(cmdline_tools_zip)
            return {"version": version, "url": url, "sha256": sha256}
    raise Error("Could not find cmdline_tools download")


def _cmdline_tools_version(cmdline_tools_zip: str) -> str:
    with zipfile.ZipFile(cmdline_tools_zip) as zf:
        with zf.open("cmdline-tools/source.properties") as fh:
            for line in fh.read().decode().splitlines():
                if m := re.match(r"Pkg.Revision=([\d.]+)", line):
                    return m[1]
    raise Error("Could not find cmdline_tools version")


def latest_nodejs_lts(current: Dict[Any, Any]) -> Optional[Dict[Any, Any]]:
    """Get latest node.js LTS from NODEJS_LTS_PAGE."""
    with requests.get(NODEJS_LTS_PAGE, timeout=60) as response:
        response.raise_for_status()
        if m := NODEJS_LTS_RX.search(response.text):
            if (version := m[1]) == current["version"]:
                return None
            url = NODEJS_LTS_LINUX_X64_XZ.format(version)
            with tempfile.TemporaryDirectory() as tmpdir:
                nodejs_lts_txz = os.path.join(tmpdir, "nodejs-lts.tar.xz")
                sha256 = download_file_with_retries(url, nodejs_lts_txz)
                _nodejs_check_sha256(version, url, sha256)
            return {"version": version, "url": url, "sha256": sha256}
    raise Error("Could not find node.js LTS download")


def _nodejs_check_sha256(version: str, url: str, sha256: str) -> None:
    file = url.rsplit("/", 1)[-1]
    with requests.get(NODEJS_SHA256SUMS.format(version), timeout=60) as response:
        response.raise_for_status()
        for line in response.text.splitlines():
            line_sha, line_file = line.split()
            if line_file == file:
                if line_sha != sha256:
                    raise Error(f"SHA-256 mismatch: downloaded {sha256!r}, upstream {line_sha!r}")
                return
    raise Error("Could not find node.js LTS upstream SHA-256")


def latest_repro_apk(current: Dict[Any, Any]) -> Optional[Dict[Any, Any]]:
    """Get latest repro-apk release from GitHub API."""
    headers = dict(Authorization=f"token {GITHUB_TOKEN}") if GITHUB_TOKEN else {}
    with requests.get(REPRO_APK_LATEST, headers=headers, timeout=60) as response:
        response.raise_for_status()
        tag = response.json()["tag_name"]
        return {"tag": tag} if tag != current["tag"] else None


def download_file(url: str, output: str) -> str:
    """Download file."""
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(output, "wb") as fh:
            sha = hashlib.sha256()
            for chunk in response.iter_content(chunk_size=4096):
                fh.write(chunk)
                sha.update(chunk)
            return sha.hexdigest()


def download_file_with_retries(url: str, output: str, *, retries: int = 5) -> str:
    """Download file w/ retries."""
    error: Exception = Error("No retries")
    for i in range(retries):
        if i:
            time.sleep(1)
        try:
            return download_file(url, output)
        except requests.RequestException as e:
            error = e
    raise error


def update_versions(*, verbose: bool = False) -> None:
    """Update versions.json."""
    versions = load_versions()
    modified = False
    if cmdline_tools := latest_cmdline_tools(versions["cmdline_tools"]):
        versions["cmdline_tools"] = cmdline_tools
        modified = True
        if verbose:
            print(f"Updated cmdline_tools to {cmdline_tools['version']}.", file=sys.stderr)
    if nodejs_lts := latest_nodejs_lts(versions["nodejs-lts"]):
        versions["nodejs-lts"] = nodejs_lts
        modified = True
        if verbose:
            print(f"Updated node.js LTS to {nodejs_lts['version']}.", file=sys.stderr)
    if repro_apk := latest_repro_apk(versions["repro-apk"]):
        versions["repro-apk"] = repro_apk
        modified = True
        if verbose:
            print(f"Updated repro-apk to {repro_apk['tag']}.", file=sys.stderr)
    if modified:
        save_versions(versions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="update versions.json")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    update_versions(verbose=args.verbose)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
