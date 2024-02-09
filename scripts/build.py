#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

# Depends: apt install aapt apksigcopier docker.io python3-requests python3-yaml

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import apksigcopier
import requests
import yaml


class Error(Exception):
    """Base class for errors."""


@dataclass(frozen=True)
class Download:
    """Download."""
    version: str
    url: str
    sha256: str

    def for_json(self) -> Dict[str, Any]:
        return dict(version=self.version, url=self.url, sha256=self.sha256)


@dataclass(frozen=True)
class Provisioning:
    """Provisioning data."""
    build_tools: Optional[str]
    cmdline_tools: Download
    image: str
    jdk: str
    ndk: Optional[str]
    platform: Optional[str]
    platform_tools: Optional[str]
    tools: Optional[str]

    def for_json(self) -> Dict[str, Any]:
        return dict(
            build_tools=self.build_tools, cmdline_tools=self.cmdline_tools.for_json(),
            image=self.image, jdk=self.jdk, ndk=self.ndk, platform=self.platform,
            platform_tools=self.platform_tools, tools=self.tools)


@dataclass(frozen=True)
class BuildRecipe:
    """Build recipe."""
    repository: str
    tag: str
    apk_url: str
    build: str
    provisioning: Provisioning

    def for_json(self) -> Dict[str, Any]:
        return dict(
            repository=self.repository, tag=self.tag, apk_url=self.apk_url,
            build=self.build, provisioning=self.provisioning.for_json())


@dataclass(frozen=True)
class AppRecipe:
    """App recipe."""
    repository: str
    versions: Tuple[BuildRecipe, ...]


# FIXME: schema + validation
def parse_yaml(recipe_file: str) -> AppRecipe:
    """Parse recipe YAML."""
    with open(recipe_file, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
        versions = []
        for v in data["versions"]:
            versions.append(BuildRecipe(
                repository=data["repository"],
                tag=v["tag"],
                apk_url=v["apk_url"].replace("$$TAG$$", v["tag"]),
                build=v["build"],
                provisioning=Provisioning(
                    build_tools=v["provisioning"]["build_tools"],
                    cmdline_tools=Download(
                        version=v["provisioning"]["cmdline_tools"]["version"],
                        url=v["provisioning"]["cmdline_tools"]["url"],
                        sha256=v["provisioning"]["cmdline_tools"]["sha256"],
                    ),
                    image=v["provisioning"]["image"],
                    jdk=v["provisioning"]["jdk"],
                    ndk=v["provisioning"]["ndk"],
                    platform=v["provisioning"]["platform"],
                    platform_tools=v["provisioning"]["platform_tools"],
                    tools=v["provisioning"]["tools"])
            ))
        return AppRecipe(repository=data["repository"], versions=tuple(versions))


# FIXME
# FIXME: stream build log to stderr
# FIXME: log hashes of .sh & .py
def build_with_docker(appid: str, recipe: BuildRecipe, *,
                      verbose: bool = False) -> Dict[Any, Any]:
    """Build recipe with docker."""
    result: Dict[str, Any] = dict(
        appid=appid, version_code=None, version_name=None,
        tag=recipe.tag, recipe=recipe.for_json(), timestamp=int(time.time()),
        reproducible=None, error=None)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = os.path.join(tmpdir, "outputs")
            scripts = os.path.join(tmpdir, "scripts")
            prepare_tmpdir(recipe, outputs=outputs, scripts=scripts)
            vercode, vername = download_apk(recipe, tmpdir, verbose=verbose)
            result.update(version_code=vercode, version_name=vername)
            pull_cmd = ("docker", "pull", "--", recipe.provisioning.image)
            run_cmd = docker_cmd(recipe, outputs=outputs, scripts=scripts)
            result["build_log"] = ""
            try:
                result["build_log"] += run_command(*pull_cmd, verbose=verbose)
                result["build_log"] += run_command(*run_cmd, verbose=verbose)
            except subprocess.CalledProcessError as e:
                result["build_log"] += e.stdout
                raise
            finally:
                if verbose:
                    print(f"--- BEGIN BUILD LOG ---\n{result['build_log']}\n"
                          "--- END BUILD LOG ---", file=sys.stderr)
            signed_sha, unsigned_sha, copied_sha, error = compare_apks(tmpdir)
            result.update(
                reproducible=signed_sha == copied_sha,  # FIXME
                upstream_signed_apk_sha256=signed_sha,
                built_unsigned_apk_sha256=unsigned_sha,
                signature_copied_apk_sha256=copied_sha,
                error=error,
            )
            return result
    except subprocess.CalledProcessError as e:
        error = f"subprocess failed: {e}"
    except FileNotFoundError as e:
        error = f"command or file not found: {e}"
    except requests.RequestException as e:
        error = f"http error: {e}"
    except Error as e:
        error = str(e)
    if verbose:
        print(f"Error: {error}", file=sys.stderr)
    return dict(result, error=error)


def prepare_tmpdir(recipe: BuildRecipe, *, outputs: str, scripts: str) -> Tuple[str, str]:
    """Prepare directories and scripts in tmpdir."""
    os.mkdir(outputs)
    os.mkdir(scripts)
    shutil.copy("scripts/provision.sh", scripts)
    build_sh = os.path.join(scripts, "build.sh")
    with open(build_sh, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/bash\nset -xeuo pipefail\n")
        fh.write('export PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/'
                 '${PROVISIONING_CMDLINE_TOOLS_VERSION}/bin"\n')
        fh.write(recipe.build + "\n")
    os.chmod(build_sh, 0o755)
    return outputs, scripts


# FIXME: configure timeout
def docker_cmd(recipe: BuildRecipe, *, outputs: str, scripts: str) -> Tuple[str, ...]:
    """Create docker run command line from recipe."""
    env = []
    for k, v in build_env(recipe).items():
        env.extend(["--env", f"{k}={v}"])
    return (
        "docker", "run", "--rm", "--workdir", "/build",
        "--volume", f"{outputs}:/outputs",
        "--volume", f"{scripts}:/scripts",
        *env, "--", recipe.provisioning.image,
        "bash", "-c", "timeout 10m /scripts/provision.sh && cd /build/repo "
                      "&& timeout 20m /scripts/build.sh"
    )


# FIXME: incomplete
def build_env(recipe: BuildRecipe) -> Dict[str, str]:
    """Create build env from recipe."""
    return dict(
        ANDROID_HOME="/opt/sdk",
        APP_REPOSITORY=recipe.repository,
        APP_TAG=recipe.tag,
        APP_APK_URL=recipe.apk_url,
        PROVISIONING_CMDLINE_TOOLS_VERSION=recipe.provisioning.cmdline_tools.version,
        PROVISIONING_CMDLINE_TOOLS_URL=recipe.provisioning.cmdline_tools.url,
        PROVISIONING_CMDLINE_TOOLS_SHA256=recipe.provisioning.cmdline_tools.sha256,
        PROVISIONING_JDK=recipe.provisioning.jdk)


def download_apk(recipe: BuildRecipe, tmpdir: str, *,
                 verbose: bool = False) -> Tuple[int, str]:
    """Download APK and get versionCode and versionName."""
    signed_apk = os.path.join(tmpdir, "upstream.apk")
    if verbose:
        print(f"Downloading {recipe.apk_url!r}...", file=sys.stderr)
    download_file(recipe.apk_url, signed_apk)
    return apk_version_info(signed_apk)


# FIXME: use repro-apk?
def apk_version_info(apkfile: str) -> Tuple[int, str]:
    """Get APK versionCode and versionName."""
    badging = subprocess.run(("aapt2", "dump", "badging", apkfile),
                             check=True, capture_output=True).stdout.decode()
    vercode = vername = None
    for x in badging.split("\n", 1)[0].split(" ")[1:]:
        k, v = x.split("=", 1)
        if k == "versionCode":
            vercode = int(v[1:-1])
        elif k == "versionName":
            vername = v[1:-1]
    if vercode is None or vername is None:
        raise Error("could not extract versionCode and versionName from aapt2 output")
    return vercode, vername


# FIXME: diff on fail?
def compare_apks(tmpdir: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Download upstream APK and compare to built APK."""
    signed_apk = os.path.join(tmpdir, "upstream.apk")
    unsigned_apk = os.path.join(tmpdir, "outputs", "unsigned.apk")
    output_apk = os.path.join(tmpdir, "copied.apk")
    signed_sha, unsigned_sha = sha256_file(signed_apk), sha256_file(unsigned_apk)
    try:
        apksigcopier.do_copy(signed_apk, unsigned_apk, output_apk, v1_only=None)
        copied_sha = sha256_file(output_apk)
        error = None
    except (apksigcopier.APKSigCopierError, zipfile.BadZipFile) as e:
        copied_sha = None
        error = f"signature copying failed: {e}"
    return signed_sha, unsigned_sha, copied_sha, error


# FIXME
# FIXME: error when tag not found
def build(*specs: str, verbose: bool = False) -> int:
    """Parse YAML & build apps."""
    errors = 0
    outputs = []
    for spec in specs:
        if verbose:
            print(f"Building {spec!r}...", file=sys.stderr)
        appid, tag = spec.split(":", 1)
        recipe = parse_yaml(os.path.join("recipes", f"{appid}.yml"))
        found = False
        for build_recipe in recipe.versions:
            if build_recipe.tag == tag:
                found = True
                outputs.append(build_with_docker(appid, build_recipe, verbose=verbose))
                break
        if not found:
            errors += 1
            print(f"Error: tag not found: {tag!r}", file=sys.stderr)
    json.dump(outputs, sys.stdout, indent=2)
    print()
    return errors


def run_command(*args: str, verbose: bool = False) -> str:
    """Run command and capture stdout + stderr."""
    if verbose:
        print(f"Running {' '.join(args)!r}...", file=sys.stderr)
    return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout.decode()


# FIXME: retry
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


def sha256_file(filename: str) -> str:
    """Calculate SHA-256 checksum of file."""
    with open(filename, "rb") as fh:
        sha = hashlib.sha256()
        while chunk := fh.read(4096):
            sha.update(chunk)
        return sha.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="build apps from recipes")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("specs", metavar="SPEC", nargs="*", help="appid:tag to build")
    args = parser.parse_args()
    if build(*args.specs, verbose=args.verbose) != 0:
        sys.exit(1)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
