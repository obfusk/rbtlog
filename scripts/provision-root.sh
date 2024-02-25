#!/bin/bash
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later
set -xeuo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get upgrade -y

readarray -d , -t extra_packages < <( printf %s "${PROVISIONING_EXTRA_PACKAGES}" )
apt-get install --no-install-recommends -y git wget unzip "${PROVISIONING_JDK}" \
  "${extra_packages[@]}"
update-alternatives --auto java

if adduser --help | grep -q -- --gecos; then
  adduser --disabled-password --gecos '' "${BUILD_USER}" --home "${BUILD_HOME_DIR}"
else
  adduser --disabled-password --comment '' "${BUILD_USER}" --home "${BUILD_HOME_DIR}"
fi

mkdir -p "${ANDROID_HOME}"
chown "${BUILD_USER}:${BUILD_USER}" "${ANDROID_HOME}"
