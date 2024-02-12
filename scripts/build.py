#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

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
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import apksigcopier
import repro_apk.binres as binres
import requests

from ruamel.yaml import YAML

BuildBackend = Enum("BuildBackend", ["PODMAN", "DOCKER"])   # FIXME


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
# FIXME: switch to ruamel.yaml
def parse_yaml(recipe_file: str) -> AppRecipe:
    """Parse recipe YAML."""
    with open(recipe_file, encoding="utf-8") as fh:
        yaml = YAML(typ="safe")
        data = yaml.load(fh)
        versions = []
        for v in data["versions"]:
            versions.append(BuildRecipe(
                repository=data["repository"],
                tag=v["tag"],
                apk_url=v["apk_url"].replace("$$TAG$$", v["tag"]),
                build="".join(line + "\n" for line in v["build"]),
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
def build_with_backend(backend: BuildBackend, appid: str, recipe: BuildRecipe, *,
                       keep_apks: Optional[str] = None, verbose: bool = False) -> Dict[Any, Any]:
    """Build recipe with backend (e.g. podman/docker)."""
    result: Dict[str, Any] = dict(
        appid=appid, version_code=None, version_name=None, tag=recipe.tag,
        recipe=recipe.for_json(), timestamp=int(time.time()), reproducible=None,
        error=None, build_log="", upstream_signed_apk_sha256=None,
        built_unsigned_apk_sha256=None, signature_copied_apk_sha256=None)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs, scripts = prepare_tmpdir(recipe, tmpdir)
            signed_sha, vercode, vername = download_apk(recipe, tmpdir, verbose=verbose)
            result.update(version_code=vercode, version_name=vername,
                          upstream_signed_apk_sha256=signed_sha)
            if backend in (BuildBackend.PODMAN, BuildBackend.DOCKER):
                pull_cmd = (backend.name.lower(), "pull", "--", recipe.provisioning.image)
                run_cmd = podman_docker_cmd(recipe, backend, outputs=outputs, scripts=scripts)
                commands = [pull_cmd, run_cmd]
            else:
                raise NotImplementedError(f"Unknown backend: {backend}")
            try:
                for cmd in commands:
                    result["build_log"] += f"RUN COMMAND {' '.join(cmd)}\n"
                    result["build_log"] += run_command(*cmd, verbose=verbose)
            except subprocess.CalledProcessError as e:
                result["build_log"] += e.stdout.decode()
                raise
            finally:
                if verbose:
                    print(f"--- BEGIN BUILD LOG ---\n{result['build_log']}\n"
                          "--- END BUILD LOG ---", file=sys.stderr)
            unsigned_sha, copied_sha, error = compare_apks(
                tmpdir, appid=appid, tag=recipe.tag, signed_sha=signed_sha,
                keep_apks=keep_apks, verbose=verbose)
            result.update(
                reproducible=signed_sha == copied_sha,  # FIXME
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


def prepare_tmpdir(recipe: BuildRecipe, tmpdir: str) -> Tuple[str, str]:
    """Prepare directories and scripts in tmpdir."""
    outputs = os.path.join(tmpdir, "outputs")
    scripts = os.path.join(tmpdir, "scripts")
    provision_root_sh = os.path.join(scripts, "provision-root.sh")
    provision_sh = os.path.join(scripts, "provision.sh")
    build_sh = os.path.join(scripts, "build.sh")
    os.chmod(tmpdir, 0o700)     # private
    os.mkdir(outputs)
    os.mkdir(scripts)
    os.chmod(outputs, 0o777)    # allow writing from within container
    os.chmod(scripts, 0o755)    # allow reading from within container
    shutil.copyfile("scripts/provision-root.sh", provision_root_sh)
    shutil.copyfile("scripts/provision.sh", provision_sh)
    os.chmod(provision_root_sh, 0o755)
    os.chmod(provision_sh, 0o755)
    with open(build_sh, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/bash\nset -xeuo pipefail\n")
        fh.write('export PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/'
                 '${PROVISIONING_CMDLINE_TOOLS_VERSION}/bin"\n')
        fh.write(recipe.build + "\n")
    os.chmod(build_sh, 0o755)
    return outputs, scripts


# FIXME: configure timeout
def podman_docker_cmd(recipe: BuildRecipe, backend: BuildBackend, *,
                      outputs: str, scripts: str) -> Tuple[str, ...]:
    """Create podman/docker run command line from recipe."""
    env = []
    for k, v in build_env(recipe).items():
        env.extend(["--env", f"{k}={v}"])
    cmd = [
        "timeout 10m /scripts/provision-root.sh",
        "cd /build",
        "timeout 10m su build /scripts/provision.sh",
        "cd /build/repo",
        "timeout 20m su build /scripts/build.sh",
    ]
    return (
        backend.name.lower(), "run", "--rm",
        "--volume", f"{outputs}:/outputs",
        "--volume", f"{scripts}:/scripts",
        *env, "--", recipe.provisioning.image,
        "bash", "-c", " && ".join(cmd))


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
                 verbose: bool = False) -> Tuple[str, int, str]:
    """Download APK and get versionCode and versionName."""
    signed_apk = os.path.join(tmpdir, "upstream.apk")
    if verbose:
        print(f"Downloading {recipe.apk_url!r}...", file=sys.stderr)
    download_file(recipe.apk_url, signed_apk)
    vercode, vername = apk_version_info(signed_apk)
    return sha256_file(signed_apk), vercode, vername


def apk_version_info(apkfile: str) -> Tuple[int, str]:
    """Get APK versionCode and versionName."""
    return binres.quick_get_idver(apkfile)[1:]


# FIXME: diff on fail?
def compare_apks(tmpdir: str, *, appid: str, tag: str, signed_sha: str,
                 keep_apks: Optional[str] = None, verbose: bool = False) \
        -> Tuple[str, Optional[str], Optional[str]]:
    """Compare upstream APK to built APK (after some checks); optionally save them."""
    signed_apk = os.path.join(tmpdir, "upstream.apk")
    unsigned_apk = os.path.join(tmpdir, "unsigned.apk")
    copied_apk = os.path.join(tmpdir, "copied.apk")
    output_apk = os.path.join(tmpdir, "outputs", "unsigned.apk")
    if not os.path.isfile(output_apk) or os.path.islink(output_apk):
        raise Error("unsigned output APK is not a regular file")
    shutil.copyfile(output_apk, unsigned_apk)
    unsigned_sha = sha256_file(unsigned_apk)
    if keep_apks:
        keep_apk(appid, tag, keep_apks, signed_apk, signed_sha, verbose=verbose)
        keep_apk(appid, tag, keep_apks, unsigned_apk, unsigned_sha, verbose=verbose)
    try:
        apksigcopier.do_copy(signed_apk, unsigned_apk, copied_apk, v1_only=None)
        copied_sha = sha256_file(copied_apk)
        error = None
    except (apksigcopier.APKSigCopierError, zipfile.BadZipFile) as e:
        copied_sha = None
        error = f"signature copying failed: {e}"
    return unsigned_sha, copied_sha, error


def keep_apk(appid: str, tag: str, output_dir: str, apkfile: str, sha256: str, *,
             verbose: bool = False) -> None:
    """Copy APK."""
    target = f"{sha256}-{appid}-{tag}-{os.path.basename(apkfile)}"
    if verbose:
        print(f"Keeping {target!r}...", file=sys.stderr)
    shutil.copyfile(apkfile, os.path.join(output_dir, target))


# FIXME
def build(backend: str, *specs: str, keep_apks: Optional[str] = None,
          verbose: bool = False) -> int:
    """Parse YAML & build apps."""
    bb = BuildBackend.__members__[backend.upper()]
    errors = 0
    outputs = []
    for spec in specs:
        if verbose:
            print(f"Building {spec!r}...", file=sys.stderr)
        appid, tag = spec.split(":", 1)
        recipe = parse_yaml(os.path.join("recipes", f"{appid}.yml"))
        build_recipe = None
        for br in recipe.versions:
            if br.tag == tag:
                build_recipe = br
                break
        if build_recipe is not None:
            outputs.append(build_with_backend(bb, appid, build_recipe,
                                              keep_apks=keep_apks, verbose=verbose))
        else:
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


# FIXME: retry, configure timeout
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
    backends = [name.lower() for name in BuildBackend.__members__]
    parser = argparse.ArgumentParser(description="build apps from recipes")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--keep-apks", metavar="DIR", help="save APKs in DIR")
    parser.add_argument("backend", choices=backends, help="backend")
    parser.add_argument("specs", metavar="SPEC", nargs="*", help="appid:tag to build")
    args = parser.parse_args()
    if build(args.backend, *args.specs, keep_apks=args.keep_apks, verbose=args.verbose) != 0:
        sys.exit(1)

# vim: set tw=80 sw=4 sts=4 et fdm=marker :
