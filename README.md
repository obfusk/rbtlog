<!-- SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net> -->
<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

[![AGPLv3+](https://img.shields.io/badge/license-AGPLv3+-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

# Reproducible Builds Transparency Log (rbtlog)

FIXME

## Scripts

FIXME

### build.py

FIXME

```bash
$ scripts/build.py --help
usage: build.py [-h] [-v] [SPEC ...]

build apps from recipes

positional arguments:
  SPEC           appid:tag to build

options:
  -h, --help     show this help message and exit
  -v, --verbose
```

### update-log.py

FIXME

```bash
$ scripts/update-log.py --help
usage: update-log.py [-h] [-v] [RECIPE ...]

update log

positional arguments:
  RECIPE         recipe

options:
  -h, --help     show this help message and exit
  -v, --verbose
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
$ apt install docker.io python3-pip python3-requests python3-yaml
$ pip install git+https://github.com/obfusk/apksigcopier.git@v1.1.1
$ pip install git+https://github.com/obfusk/reproducible-apk-tools.git@binres-20240211
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
