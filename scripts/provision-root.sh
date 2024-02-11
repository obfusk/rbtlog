#!/bin/bash
set -xeuo pipefail

apt-get update
apt-get upgrade

apt-get install --no-install-recommends -y git wget unzip "${PROVISIONING_JDK}"
update-alternatives --auto java

adduser --disabled-password --comment '' build --home /build
mkdir -p "${ANDROID_HOME}"
chown build:build "${ANDROID_HOME}"
