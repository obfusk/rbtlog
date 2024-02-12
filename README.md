<!-- SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net> -->
<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

[![AGPLv3+](https://img.shields.io/badge/license-AGPLv3+-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

# Reproducible Builds Transparency Log (rbtlog)

FIXME

## Scripts

FIXME

### build.py

FIXME

For each specified `<appid>:<tag>`, reads `recipes/<appid>.yml` and builds the
requested tag from its recipe (using the specified backend, e.g. podman or
docker) and produces JSON output on stdout; with `--verbose` also produces
status messages and a build log on stderr.

```bash
$ scripts/build.py --help
usage: build.py [-h] [-v] [--keep-apks DIR] {podman,docker} [SPEC ...]

build apps from recipes

positional arguments:
  {podman,docker}  backend
  SPEC             appid:tag to build

options:
  -h, --help       show this help message and exit
  -v, --verbose
  --keep-apks DIR  save APKs in DIR

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

### update-log.py

FIXME

For each specified `/path/to/<appid>.yml` (e.g. `recipes/*.yml`), makes a list
of `<appid>:<tag>` pairs not already in `logs/<appid>.json`, runs `build.py` to
build them, and adds the resulting output to `logs/<appid>.json`.

```bash
$ scripts/update-log.py --help
usage: update-log.py [-h] [-v] {podman,docker} [RECIPE ...]

update log

positional arguments:
  {podman,docker}  backend
  RECIPE           recipe

options:
  -h, --help       show this help message and exit
  -v, --verbose

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

### update-recipes.py

FIXME

For each specified `/path/to/<appid>.yml` (e.g. `recipes/*.yml`), checks the
relevant forge (e.g. GitHub) for the latest release tag (and APK URL) and adds a
new entry in the recipe (unless that tag already has an entry).

```bash
FIXME
```

### provision-root.sh & provision.sh

FIXME

## Recipes

FIXME

### Catima

FIXME

```yaml
---
repository: https://github.com/CatimaLoyalty/Android.git
versions:
  - tag: v2.27.0
    apk_url: https://github.com/CatimaLoyalty/Android/releases/download/$$TAG$$/app-release.apk
    build: |
      ./gradlew assembleRelease
      mv app/build/outputs/apk/release/app-release-unsigned.apk /outputs/unsigned.apk
    provisioning:
      build_tools: null
      cmdline_tools:
        version: '12.0'
        url: https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
        sha256: 2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258
      image: debian:bookworm-slim
      jdk: openjdk-17-jdk-headless
      ndk: null
      platform: null
      platform_tools: null
      tools: null
```

## GitHub Actions workflows

### ci

FIXME

### update-log

FIXME

## Installing

FIXME

## Dependencies

FIXME

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
