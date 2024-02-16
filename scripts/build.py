#!/usr/bin/python3
# encoding: utf-8
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import hashlib
import json
import os
import re
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
    android_home: str
    build_tools: Optional[str]
    cmake: Optional[str]
    cmdline_tools: Download
    extra_packages: Tuple[str, ...]
    image: str
    jdk: str
    ndk: Optional[str]
    platform: Optional[str]
    platform_tools: Optional[str]
    tools: Optional[str]

    def for_json(self) -> Dict[str, Any]:
        return dict(
            android_home=self.android_home, build_tools=self.build_tools, cmake=self.cmake,
            cmdline_tools=self.cmdline_tools.for_json(), extra_packages=self.extra_packages,
            image=self.image, jdk=self.jdk, ndk=self.ndk, platform=self.platform,
            platform_tools=self.platform_tools, tools=self.tools)


@dataclass(frozen=True)
class BuildRecipe:
    """Build recipe."""
    repository: str
    tag: str
    apk_pattern: str
    apk_url: str
    build: str
    build_home_dir: str
    build_repo_dir: str
    build_user: str
    provisioning: Provisioning

    def for_json(self) -> Dict[str, Any]:
        return dict(
            repository=self.repository, tag=self.tag, apk_pattern=self.apk_pattern,
            apk_url=self.apk_url, build=self.build, build_home_dir=self.build_home_dir,
            build_repo_dir=self.build_repo_dir, build_user=self.build_user,
            provisioning=self.provisioning.for_json())


@dataclass(frozen=True)
class AppRecipe:
    """App recipe."""
    repository: str
    updates: str
    versions: Tuple[BuildRecipe, ...]


def parse_yaml(recipe_file: str) -> AppRecipe:
    r"""
    Parse recipe YAML.

    >>> data = parse_yaml("recipes/me.hackerchick.catima.yml")
    >>> data.repository
    'https://github.com/CatimaLoyalty/Android.git'
    >>> data.updates
    'releases'
    >>> data.versions[0]
    BuildRecipe(repository='https://github.com/CatimaLoyalty/Android.git', tag='v2.27.0', apk_pattern='app-release\\.apk', apk_url='https://github.com/CatimaLoyalty/Android/releases/download/v2.27.0/app-release.apk', build='./gradlew assembleRelease\nmv app/build/outputs/apk/release/app-release-unsigned.apk /outputs/unsigned.apk\n', build_home_dir='/build', build_repo_dir='/build/repo', build_user='build', provisioning=Provisioning(android_home='/opt/sdk', build_tools=None, cmake=None, cmdline_tools=Download(version='12.0', url='https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip', sha256='2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258'), extra_packages=(), image='debian:bookworm-slim', jdk='openjdk-17-jdk-headless', ndk=None, platform=None, platform_tools=None, tools=None))

    """
    with open(recipe_file, encoding="utf-8") as fh:
        yaml = YAML(typ="safe")
        data = yaml.load(fh)
        versions = []
        tag_pattern = data["updates"][5:] if data["updates"].startswith("tags:") else None
        for vsn in data["versions"]:
            tag = vsn["tag"]
            for apk in vsn["apks"]:
                apk_url = url_with_replacements(apk["apk_url"], tag, tag_pattern)
                prov = apk["provisioning"]
                versions.append(BuildRecipe(
                    repository=data["repository"],
                    tag=tag,
                    apk_pattern=apk["apk_pattern"],
                    apk_url=apk_url,
                    build="".join(line + "\n" for line in apk["build"]),
                    build_home_dir=apk["build_home_dir"],
                    build_repo_dir=apk["build_repo_dir"],
                    build_user=apk["build_user"],
                    provisioning=Provisioning(
                        android_home=prov["android_home"],
                        build_tools=prov["build_tools"],
                        cmake=prov["cmake"],
                        cmdline_tools=Download(
                            version=prov["cmdline_tools"]["version"],
                            url=prov["cmdline_tools"]["url"],
                            sha256=prov["cmdline_tools"]["sha256"],
                        ),
                        extra_packages=tuple(prov["extra_packages"]),
                        image=prov["image"],
                        jdk=prov["jdk"],
                        ndk=prov["ndk"],
                        platform=prov["platform"],
                        platform_tools=prov["platform_tools"],
                        tools=prov["tools"])
                ))
        return AppRecipe(repository=data["repository"], updates=data["updates"],
                         versions=tuple(versions))


def url_with_replacements(apk_url: str, tag: str, tag_pattern: Optional[str]) -> str:
    """URL with $$TAG$$ $$TAG:1$$ etc. replaced."""
    url = apk_url.replace("$$TAG$$", tag)
    if tag_pattern and (m := re.fullmatch(tag_pattern, tag)):
        for i, group in enumerate(m.groups("")):
            url = url.replace(f"$$TAG:{i + 1}$$", group)
    return url


# FIXME
def build_with_backend(backend: BuildBackend, appid: str, recipe: BuildRecipe, *,
                       keep_apks: Optional[str] = None, verbose: bool = False) -> Dict[Any, Any]:
    """Build recipe with backend (e.g. podman/docker)."""
    result: Dict[str, Any] = dict(
        appid=appid, version_code=None, version_name=None, tag=recipe.tag, commit=None,
        recipe=recipe.for_json(), timestamp=int(time.time()), reproducible=None,
        error=None, build_log="", upstream_signed_apk_sha256=None,
        built_unsigned_apk_sha256=None, signature_copied_apk_sha256=None)
    try:
        commit = result["commit"] = tag_to_commit(recipe.repository, recipe.tag)
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs, scripts = prepare_tmpdir(recipe, tmpdir)
            signed_sha, vercode, vername = download_apk(recipe, appid, tmpdir, verbose=verbose)
            result.update(version_code=vercode, version_name=vername,
                          upstream_signed_apk_sha256=signed_sha)
            if backend in (BuildBackend.PODMAN, BuildBackend.DOCKER):
                pull_cmd = (backend.name.lower(), "pull", "--", recipe.provisioning.image)
                run_cmd = podman_docker_cmd(recipe, backend, commit, outputs=outputs, scripts=scripts)
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
def podman_docker_cmd(recipe: BuildRecipe, backend: BuildBackend, commit: str, *,
                      outputs: str, scripts: str) -> Tuple[str, ...]:
    """Create podman/docker run command line from recipe."""
    env, benv = [], build_env(recipe, commit)
    for k, v in benv.items():
        env.extend(["--env", f"{k}={v}"])
    cmd = [
        "timeout 10m /scripts/provision-root.sh",
        f"cd {benv['BUILD_HOME_DIR']}",
        f"timeout 10m su {benv['BUILD_USER']} /scripts/provision.sh",
        f"cd {benv['BUILD_REPO_DIR']}",
        f"timeout 20m su {benv['BUILD_USER']} /scripts/build.sh",
    ]
    return (
        backend.name.lower(), "run", "--rm",
        "--volume", f"{outputs}:/outputs",
        "--volume", f"{scripts}:/scripts",
        *env, "--", recipe.provisioning.image,
        "bash", "-c", " && ".join(cmd))


def build_env(recipe: BuildRecipe, commit: str) -> Dict[str, str]:
    """Create build env from recipe."""
    return dict(
        ANDROID_HOME=recipe.provisioning.android_home,
        APP_REPOSITORY=recipe.repository,
        APP_TAG=recipe.tag,
        APP_COMMIT=commit,
        BUILD_USER=recipe.build_user,
        BUILD_HOME_DIR=recipe.build_home_dir,
        BUILD_REPO_DIR=recipe.build_repo_dir,
        PROVISIONING_BUILD_TOOLS=recipe.provisioning.build_tools or "",
        PROVISIONING_CMAKE=recipe.provisioning.cmake or "",
        PROVISIONING_CMDLINE_TOOLS_VERSION=recipe.provisioning.cmdline_tools.version,
        PROVISIONING_CMDLINE_TOOLS_URL=recipe.provisioning.cmdline_tools.url,
        PROVISIONING_CMDLINE_TOOLS_SHA256=recipe.provisioning.cmdline_tools.sha256,
        PROVISIONING_EXTRA_PACKAGES=",".join(recipe.provisioning.extra_packages),
        PROVISIONING_JDK=recipe.provisioning.jdk,
        PROVISIONING_NDK=recipe.provisioning.ndk or "",
        PROVISIONING_PLATFORM=recipe.provisioning.platform or "",
        PROVISIONING_PLATFORM_TOOLS=recipe.provisioning.platform_tools or "",
        PROVISIONING_TOOLS=recipe.provisioning.tools or "")


def download_apk(recipe: BuildRecipe, appid: str, tmpdir: str, *,
                 verbose: bool = False) -> Tuple[str, int, str]:
    """Download APK and get versionCode and versionName."""
    signed_apk = os.path.join(tmpdir, "upstream.apk")
    if verbose:
        print(f"Downloading {recipe.apk_url!r}...", file=sys.stderr)
    download_file(recipe.apk_url, signed_apk)
    appid_from_apk, vercode, vername = apk_version_info(signed_apk)
    if appid != appid_from_apk:
        raise Error(f"APK appid mismatch: expected {appid}, got {appid_from_apk}")
    return sha256_file(signed_apk), vercode, vername


def apk_version_info(apkfile: str) -> Tuple[str, int, str]:
    """Get APK appid, versionCode, versionName."""
    return binres.quick_get_idver(apkfile)


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
    shutil.copyfile(output_apk, unsigned_apk)   # copy w/o permission bits!
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
        build_recipes = [br for br in recipe.versions if br.tag == tag]
        if build_recipes:
            for br in build_recipes:
                outputs.append(build_with_backend(bb, appid, br, keep_apks=keep_apks, verbose=verbose))
        else:
            errors += 1
            print(f"Error: tag not found: {tag!r}", file=sys.stderr)
    json.dump(outputs, sys.stdout, indent=2)
    print()
    return errors


def run_command(*args: str, verbose: bool = False) -> str:
    r"""
    Run command and capture stdout + stderr.

    >>> run_command("echo", "OK")
    'OK\n'
    >>> run_command("bash", "-c", "echo OK >&2")
    'OK\n'
    >>> try:
    ...     run_command("false")
    ... except subprocess.CalledProcessError as e:
    ...     print(e)
    Command '('false',)' returned non-zero exit status 1.

    """
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
    r"""
    Calculate SHA-256 checksum of file.

    >>> sha256_file("/dev/null")
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

    """
    with open(filename, "rb") as fh:
        sha = hashlib.sha256()
        while chunk := fh.read(4096):
            sha.update(chunk)
        return sha.hexdigest()


def tag_to_commit(repository: str, tag: str) -> str:
    r"""
    Get commit hash for tag.

    >>> tag_to_commit("https://github.com/CatimaLoyalty/Android.git", "v2.27.0")
    '84c343e41f4a09ee3fe6ee0924a3446ae325c4b7'
    >>> tag_to_commit("https://github.com/threema-ch/threema-android.git", "5.2.3")
    '14388d856b28bdbe1417d0f92fed09567263c36e'

    """
    output = run_command("git", "ls-remote", "--tags", "--", repository)
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
    raise Error(f"tag not found: {tag}")


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
