#!/bin/bash
set -xeuo pipefail

mkdir -p "${ANDROID_HOME}"/cmdline-tools

wget -q -O /tmp/tools.zip -- "${PROVISIONING_CMDLINE_TOOLS_URL}"
sha256sum -c <<< "${PROVISIONING_CMDLINE_TOOLS_SHA256}  /tmp/tools.zip"
unzip -q -d "${ANDROID_HOME}"/cmdline-tools /tmp/tools.zip
mv "${ANDROID_HOME}"/cmdline-tools/{cmdline-tools,"${PROVISIONING_CMDLINE_TOOLS_VERSION}"}
rm /tmp/tools.zip

export PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/${PROVISIONING_CMDLINE_TOOLS_VERSION}/bin"
( yes || true ) | sdkmanager --sdk_root="${ANDROID_HOME}" --licenses

git clone --recurse-submodules -b "${APP_TAG}" -- "${APP_REPOSITORY}" /build/repo
cd /build/repo
test "$( git rev-parse HEAD )" = "${APP_COMMIT}"
