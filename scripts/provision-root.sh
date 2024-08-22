#!/bin/bash
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later
set -xeuo pipefail

export DEBIAN_FRONTEND=noninteractive

if [ -n "${HTTP_PROXY:-}" ]; then
  printf 'Acquire::http::Proxy "%s";\n' "$HTTP_PROXY" >> /etc/apt/apt.conf.d/proxy
fi
if [ -n "${HTTPS_PROXY:-}" ]; then
  printf 'Acquire::https::Proxy "%s";\n' "$HTTPS_PROXY" >> /etc/apt/apt.conf.d/proxy
fi

apt-get update
apt-get upgrade -y
apt-get install --no-install-recommends -y git wget unzip "${PROVISIONING_JDK}"

if [ -n "${PROVISIONING_EXTRA_PACKAGES}" ]; then
  readarray -d , -t extra_packages < <( printf %s "${PROVISIONING_EXTRA_PACKAGES}" )
  apt-get install --no-install-recommends -y "${extra_packages[@]}"
fi

update-alternatives --auto java

if adduser --help | grep -q -- --gecos; then
  adduser --disabled-password --gecos '' "${BUILD_USER}" --home "${BUILD_HOME_DIR}"
else
  adduser --disabled-password --comment '' "${BUILD_USER}" --home "${BUILD_HOME_DIR}"
fi

mkdir -p /opt "${ANDROID_HOME}"
chown "${BUILD_USER}:${BUILD_USER}" /opt "${ANDROID_HOME}"
