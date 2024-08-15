<!-- SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net> -->
<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

[![CI](https://github.com/obfusk/rbtlog/actions/workflows/ci.yml/badge.svg)](https://github.com/obfusk/rbtlog/actions/workflows/ci.yml)
[![podman](https://github.com/obfusk/rbtlog/actions/workflows/podman.yml/badge.svg?branch=master)](https://github.com/obfusk/rbtlog/actions/workflows/podman.yml)
[![docker](https://github.com/obfusk/rbtlog/actions/workflows/docker.yml/badge.svg?branch=master)](https://github.com/obfusk/rbtlog/actions/workflows/docker.yml)
[![update log](https://github.com/obfusk/rbtlog/actions/workflows/update-log.yml/badge.svg)](https://github.com/obfusk/rbtlog/actions/workflows/update-log.yml)
[![update recipes](https://github.com/obfusk/rbtlog/actions/workflows/update-recipes.yml/badge.svg)](https://github.com/obfusk/rbtlog/actions/workflows/update-recipes.yml)
[![AGPLv3+](https://img.shields.io/badge/license-AGPLv3+-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

# Reproducible Builds Transparency Log (rbtlog)

`rbtlog` is a [Reproducible Builds](https://reproducible-builds.org/)
transparency log for Android APKs.  Its `git` repository contains:

- [Scripts](#scripts) forming a rebuilder framework.
- [Recipes](#recipes) to build various apps.
- [Rebuild Logs](#rebuild-logs) forming a transparency log of reproduction attempts.
- [GitHub Actions workflows](#github-actions-workflows) to automate everything.

## Announcing Android Reproducible Builds at IzzyOnDroid with rbtlog

<details>

[IzzyOnDroid](https://apt.izzysoft.de/fdroid/) is the largest 3rd-party
F-Droid-compatible repository of open source Android apps (almost 1200
currently), publishing a collection of official binaries (APKs) built by the
original application developers and provided via repositories on GitHub, GitLab,
Codeberg, etc.  It provides a convenient way to install and update apps, as well
as additional security and transparency via multiple [custom scans and
checks](https://android.izzysoft.de/articles/named/iod-scan-apkchecks).

[rbtlog](https://github.com/obfusk/rbtlog) is a Reproducible Builds transparency
log for Android APKs.  Its git repository contains scripts forming a rebuilder
framework, recipes to build various apps, rebuild logs forming a transparency
log of reproduction attempts, and CI workflows to automate everything.  It
allows anyone to easily run a rebuilder for any apps available from a git
repository with release tags plus accompanying APKs built and signed by the
developer.

The rbtlog I run currently provides rebuild logs for dozens of apps available
via IzzyOnDroid as well as e.g. NewPipe and Threema.  Izzy himself runs another
[rbtlog instance](https://codeberg.org/IzzyOnDroid/rbtlog) providing coverage of
even more IzzyOnDroid apps.  And there are more to come!

</details>

We are pleased to announce ["Reproducible Builds, special client support and more
in our repo"](https://android.izzysoft.de/articles/named/iod-rbs-mirrors-clients):
a collaboration between various independent interoperable projects: the
IzzyOnDroid team, 3rd-party clients Droid-ify & Neo Store, and rbtlog (part of my
collection of tools for Android Reproducible Builds) to bring Reproducible Builds
to IzzyOnDroid and the wider Android ecosystem.

\- Fay

## Security

The current build setup only supports building inside a container (using
`podman` or `docker`), which does not provide the isolation of a full VM (though
hopefully `libvirt`/`debvm` support will be added eventually).  There are some
safeguards against trivial container breakouts, rootless `podman` is supported
and recommended, and the build runs with as few privileges as possible inside
the container, but there are no guarantees.  GitHub Actions uses ephemeral VMs,
which does reduce the risk somewhat when using that to build.

Commits should always be reviewed and signed using the key specified in
`about.json` (which the build infrastructure should absolutely not have access
to).  Anyone running their own rebuilder instance should evaluate the risks
involved.  We do not recommend building untrusted apps without further
safeguards.

## Scripts

The scripts in `scripts/` provide the rebuilder component.

### build.py

Builds unsigned APKs from apps' recipes and compares them to the signed APKs
published by the upstream developer(s) using
[`apksigcopier`](https://github.com/obfusk/apksigcopier).

For each specified `<appid>:<tag>`, reads `recipes/<appid>.yml` and builds the
requested tag from its recipe (using the specified backend, e.g. `podman` or
`docker`) and produces JSON output on stdout; with `--verbose` also produces
status messages and a build log on stderr.

<details>

```bash
$ scripts/build.py --help
usage: build.py [-h] [-v] [--keep-apks DIR] [--local]
                {podman,docker} [SPEC ...]

build apps from recipes

positional arguments:
  {podman,docker}  backend
  SPEC             APPID:TAG to build

options:
  -h, --help       show this help message and exit
  -v, --verbose
  --keep-apks DIR  save APKs in DIR
  --local          allow APPID:TAG:[COMMIT]:[APK|none] build SPECs

$ scripts/build.py -v podman me.hackerchick.catima:v2.27.0
Building 'me.hackerchick.catima:v2.27.0'...
Downloading 'https://github.com/CatimaLoyalty/Android/releases/download/v2.27.0/app-release.apk'...
Running 'podman pull -- debian:bookworm-slim'...
Running 'podman run --rm --volume [...]:/outputs --volume [...]:/scripts --env ANDROID_HOME=/opt/sdk [...] -- debian:bookworm-slim bash -c timeout 10m /scripts/provision-root.sh && cd /build && timeout 10m su build /scripts/provision.sh && cd /build/repo && timeout 20m su build /scripts/build.sh'...
--- BEGIN BUILD LOG ---
[...]
BUILD SUCCESSFUL in 3m 30s
42 actionable tasks: 42 executed
+ mv app/build/outputs/apk/release/app-release-unsigned.apk /outputs/unsigned.apk

--- END BUILD LOG ---
[
  {
    "appid": "me.hackerchick.catima",
    "version_code": 132,
    "version_name": "2.27.0",
    "tag": "v2.27.0",
    "commit": "84c343e41f4a09ee3fe6ee0924a3446ae325c4b7",
    "recipe": { [...] },
    "timestamp": 1707523651,
    "reproducible": true,
    "error": null,
    "build_log": "[...]",
    "upstream_signed_apk_sha256": "406d52cb1c778444521adffc1d82afeaff37c0a2e33d3c9888a9e0361bcbd0fd",
    "built_unsigned_apk_sha256": "fd20af0e28807dd85f3ff910069a966f82302d543e93cd1de2da0ba68851c2ee",
    "signature_copied_apk_sha256": "406d52cb1c778444521adffc1d82afeaff37c0a2e33d3c9888a9e0361bcbd0fd"
  }
]
```

</details>

### update-log.py

Updates the transparency log by rebuilding all tags for the specified apps'
recipes that are not yet part of the log.

For each specified `/path/to/<appid>.yml` (e.g. `recipes/*.yml`), makes a list
of `<appid>:<tag>` pairs not already in `logs/<appid>.json`, runs `build.py` to
build them, and adds the resulting output to `logs/<appid>.json`.

<details>

```bash
$ scripts/update-log.py --help
usage: update-log.py [-h] [-v] [--batch N] [--keep-apks DIR]
                     {podman,docker} [RECIPE ...]

update log

positional arguments:
  {podman,docker}  backend
  RECIPE           recipe

options:
  -h, --help       show this help message and exit
  -v, --verbose
  --batch N        stop after N builds
  --keep-apks DIR  save APKs in DIR

$ scripts/update-log.py -v docker recipes/*.yml
Updating 'me.hackerchick.catima'...
Nothing to build.
Updating 'org.fossify.gallery'...
Nothing to build.
Updating 'org.fossify.messages'...
Building ['org.fossify.messages:1.0.1']...
Building 'org.fossify.messages:1.0.1'...
Downloading 'https://github.com/FossifyOrg/Messages/releases/download/1.0.1/messages-2-foss-release.apk'...
Running 'docker pull -- debian:bookworm-slim'...
Running 'docker run [...]'...
--- BEGIN BUILD LOG ---
RUN COMMAND docker pull -- debian:bookworm-slim
bookworm-slim: Pulling from library/debian
c57ee5000d61: Pulling fs layer
c57ee5000d61: Download complete
c57ee5000d61: Pull complete
Digest: sha256:7802002798b0e351323ed2357ae6dc5a8c4d0a05a57e7f4d8f97136151d3d603
Status: Downloaded newer image for debian:bookworm-slim
docker.io/library/debian:bookworm-slim
RUN COMMAND docker run [...]
[...]
+ apt-get install --no-install-recommends -y git wget unzip openjdk-17-jdk-headless
[...]
+ git clone --recurse-submodules -b 1.0.1 -- https://github.com/FossifyOrg/Messages.git /build/repo
[...]
+ ./gradlew assembleFossRelease
[...]
BUILD SUCCESSFUL in 4m 49s
42 actionable tasks: 42 executed
+ mv app/build/outputs/apk/foss/release/messages-2-foss-release-unsigned.apk /outputs/unsigned.apk

--- END BUILD LOG ---
```

</details>

### update-recipes.py

Updates the apps' recipes by checking upstreams' forges for new latest releases.

For each specified `/path/to/<appid>.yml` (e.g. `recipes/*.yml`), checks the
relevant forge (e.g. GitHub) for the latest release tag (and APK URL) and adds a
new entry in the recipe (unless that tag already has an entry).

<details>

```bash
$ scripts/update-recipes.py --help
usage: update-recipes.py [-h] [-q] [-v] [--continue-on-errors] [RECIPE ...]

update recipes

positional arguments:
  RECIPE                recipe

options:
  -h, --help            show this help message and exit
  -q, --quiet
  -v, --verbose
  --continue-on-errors  continue on errors

$ scripts/update-recipes.py -v recipes/*.yml
Updating 'me.hackerchick.catima'...
Checking 'https://api.github.com/repos/CatimaLoyalty/Android/releases/latest'...
Found tag 'v2.27.0' with APK URL 'https://github.com/CatimaLoyalty/Android/releases/download/v2.27.0/app-release.apk'.
Updating 'org.fossify.gallery'...
Checking 'https://api.github.com/repos/FossifyOrg/Gallery/releases/latest'...
Found tag '1.1.1' with APK URL 'https://github.com/FossifyOrg/Gallery/releases/download/1.1.1/gallery-5-foss-release.apk'.
Tag already present: '1.1.1'.
Updating 'org.fossify.messages'...
Checking 'https://api.github.com/repos/FossifyOrg/Messages/releases/latest'...
Found tag '1.0.1' with APK URL 'https://github.com/FossifyOrg/Messages/releases/download/1.0.1/messages-2-foss-release.apk'.
Tag already present: '1.0.1'.
```

</details>

### make-index.py

Processes each specified `/path/to/<appid>.json` rebuild log file and produces a
JSON index on stdout.  This index maps each upstream APK's SHA-256 checksum to a
summary of its rebuild results.

NB: work in progress; output format may change.

NB: ideally there are only rebuild results for the tag corresponding to the
version code/name of the APK, but this cannot be guaranteed as it may have been
attached to another tag (by mistake).

<details>

```bash
$ scripts/make-index.py --help
usage: make-index.py [-h] [-v] [LOG ...]

make index

positional arguments:
  LOG            log

options:
  -h, --help     show this help message and exit
  -v, --verbose

$ scripts/make-index.py -v logs/*.json
Processing 'com.bnyro.translate'...
Processing 'com.looker.droidify'...
Processing 'me.hackerchick.catima'...
Processing 'org.fossify.gallery'...
Processing 'org.fossify.messages'...
{
  "11d413edcbc200f1497f68613adb56fb7a8d748c180a215782e98bff263506e5": [
    {
      "repository": "https://github.com/you-apps/TranslateYou.git",
      "apk_url": "https://github.com/you-apps/TranslateYou/releases/download/v9.0/app-libre-release.apk",
      "appid": "com.bnyro.translate",
      "version_code": 40,
      "version_name": "9.0",
      "tag": "v9.0",
      "commit": "3bbc2dbe09d8928529df00ebe9f46556aebc5146",
      "timestamp": 1707876803,
      "reproducible": true,
      "error": null
    }
  ],
  [...]
  "406d52cb1c778444521adffc1d82afeaff37c0a2e33d3c9888a9e0361bcbd0fd": [
    {
      "repository": "https://github.com/CatimaLoyalty/Android.git",
      "apk_url": "https://github.com/CatimaLoyalty/Android/releases/download/v2.27.0/app-release.apk",
      "appid": "me.hackerchick.catima",
      "version_code": 132,
      "version_name": "2.27.0",
      "tag": "v2.27.0",
      "commit": "84c343e41f4a09ee3fe6ee0924a3446ae325c4b7",
      "timestamp": 1707877480,
      "reproducible": true,
      "error": null
    }
  ],
  [...]
}
```

</details>

### provision-root.sh & provision.sh

These scripts are used by `build.py` to provision the build environment (e.g. in
a `podman` container): installing required packages and the Android SDK, cloning
the app's repository, etc.

## Recipes

The YAML recipes in `recipes/` provide the (re)build instructions for individual
apps.  For example, the build recipe for Catima looks like this:

<details>

```yaml
---
repository: https://github.com/CatimaLoyalty/Android.git
updates: releases
versions:
  - tag: v2.27.0
    apks:
      - apk_pattern: app-release\.apk
        apk_url: https://github.com/CatimaLoyalty/Android/releases/download/$$TAG$$/app-release.apk
        build:
          - ./gradlew assembleRelease
          - mv app/build/outputs/apk/release/app-release-unsigned.apk /outputs/unsigned.apk
        build_home_dir: /build
        build_repo_dir: /build/repo
        build_user: build
        provisioning:
          android_home: /opt/sdk
          build_tools:
          cmake:
          cmdline_tools:
            version: '12.0'
            url: https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
            sha256: 2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258
          extra_packages: []
          image: debian:bookworm-slim
          jdk: openjdk-17-jdk-headless
          ndk:
          platform:
          platform_tools:
          tools:
          verify_gradle_wrapper: true
```

</details>

## Rebuild Logs

The JSON rebuild logs in the `logs/` directory of this `git` repository form a
transparency log of reproduction attempts.

NB: this directory, `index.json`, and `about.json` are only present on
the (default) `log` branch, which is otherwise identical to the
`master` branch.

For example, the rebuild log for Catima looks like this:

<details>

```json
{
  "appid": "me.hackerchick.catima",
  "tags": {
    "v2.27.0": [
      {
        "appid": "me.hackerchick.catima",
        "version_code": 132,
        "version_name": "2.27.0",
        "tag": "v2.27.0",
        "commit": "84c343e41f4a09ee3fe6ee0924a3446ae325c4b7",
        "recipe": {
          "repository": "https://github.com/CatimaLoyalty/Android.git",
          "tag": "v2.27.0",
          "apk_pattern": "app-release\\.apk",
          "apk_url": "https://github.com/CatimaLoyalty/Android/releases/download/v2.27.0/app-release.apk",
          "build": "./gradlew assembleRelease\nmv app/build/outputs/apk/release/app-release-unsigned.apk /outputs/unsigned.apk\n",
          "build_home_dir": "/build",
          "build_repo_dir": "/build/repo",
          "build_user": "build",
          "provisioning": {
            "android_home": "/opt/sdk",
            "build_tools": null,
            "cmake": null,
            "cmdline_tools": {
              "version": "12.0",
              "url": "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip",
              "sha256": "2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258"
            },
            "extra_packages": [],
            "image": "debian:bookworm-slim",
            "jdk": "openjdk-17-jdk-headless",
            "ndk": null,
            "platform": null,
            "platform_tools": null,
            "tools": null
          }
        },
        "timestamp": 1707618660,
        "reproducible": true,
        "error": null,
        "build_log": "[...]"
        "upstream_signed_apk_sha256": "406d52cb1c778444521adffc1d82afeaff37c0a2e33d3c9888a9e0361bcbd0fd",
        "built_unsigned_apk_sha256": "fd20af0e28807dd85f3ff910069a966f82302d543e93cd1de2da0ba68851c2ee",
        "signature_copied_apk_sha256": "406d52cb1c778444521adffc1d82afeaff37c0a2e33d3c9888a9e0361bcbd0fd"
      }
    ]
  },
  "version_codes": {
    "132": [
      "v2.27.0"
    ]
  },
  "sha256": {
    "406d52cb1c778444521adffc1d82afeaff37c0a2e33d3c9888a9e0361bcbd0fd": [
      "v2.27.0"
    ]
  }
}
```

</details>

## GitHub Actions workflows

### ci.yml, podman.yml, docker.yml

CI for the rebuilder itself (code linting etc.).

### update-log.yml

Automatically runs `scripts/update-log.py -v podman recipes/*.yml` every day and
creates a pull request with the changes.  The pull request is reviewed and
signed before being merged into the `log` branch.

### update-recipes.yml

Automatically runs `scripts/update-recipes.py -v recipes/*.yml` every day and
creates a pull request with the changes.  The pull request is reviewed and
signed before being merged into the `master` and `log` branches.

## JSON Schemas

There are JSON Schemas to validate the YAML recipes, JSON logs, and `index.json`
in `schemas/`.

## Installing

Everything but the dependencies is contained in the `git` repository.

```bash
$ git clone https://github.com/obfusk/rbtlog.git    # main repository @ github.com
$ git clone https://gitlab.com/obfusk/rbtlog.git    # mirror @ gitlab.com
$ git clone https://codeberg.org/obfusk/rbtlog.git  # mirror @ codeberg.org
```

## Dependencies

Python >= 3.8 + several libraries (`requests`, `ruamel.yaml`) + `apksigcopier` +
`reproducible-apk-tools` + a backend like `podman` or `docker`.

### Debian/Ubuntu

```bash
$ apt install podman python3-pip    # can also use docker.io instead of podman
$ pip install -r requirements.txt   # may need/want to use a venv
```

### Docker security

```bash
$ cat /etc/docker/daemon.json
{
  "userns-remap": "default"
}
```

## License

[![AGPLv3+](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.html)

<!-- vim: set tw=70 sw=2 sts=2 et fdm=marker : -->
