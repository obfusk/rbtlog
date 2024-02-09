#!/bin/bash
set -euo pipefail

apt-get update
apt-get upgrade

apt-get install -y git wget unzip "${PROVISIONING_JDK}"
update-alternatives --auto java

mkdir -p "${ANDROID_HOME}"/cmdline-tools

wget -O /tmp/tools.zip -- "${PROVISIONING_CMDLINE_TOOLS_URL}"
sha256sum -c <<< "${PROVISIONING_CMDLINE_TOOLS_SHA256}  /tmp/tools.zip"
unzip -q -d "${ANDROID_HOME}"/cmdline-tools /tmp/tools.zip
mv "${ANDROID_HOME}"/cmdline-tools/{cmdline-tools,"${PROVISIONING_CMDLINE_TOOLS_VERSION}"}
rm /tmp/tools.zip

git clone "${APP_REPOSITORY}" /build/repo
