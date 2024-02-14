#!/bin/bash
set -xeuo pipefail

apt-get update
apt-get upgrade -y

readarray -d , -t extra_packages < <( printf %s "${PROVISIONING_EXTRA_PACKAGES}" )
apt-get install --no-install-recommends -y git wget unzip "${PROVISIONING_JDK}" \
  "${extra_packages[@]}"
update-alternatives --auto java

adduser --disabled-password --comment '' "${BUILD_USER}" --home "${BUILD_HOME_DIR}"
mkdir -p "${ANDROID_HOME}"
chown "${BUILD_USER}:${BUILD_USER}" "${ANDROID_HOME}"
