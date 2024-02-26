#!/bin/bash
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later
set -xeuo pipefail

mkdir -p "${ANDROID_HOME}"/cmdline-tools

wget -q -O /tmp/tools.zip -- "${PROVISIONING_CMDLINE_TOOLS_URL}"
sha256sum -c <<< "${PROVISIONING_CMDLINE_TOOLS_SHA256}  /tmp/tools.zip"
unzip -q -d "${ANDROID_HOME}"/cmdline-tools /tmp/tools.zip
mv "${ANDROID_HOME}"/cmdline-tools/{cmdline-tools,"${PROVISIONING_CMDLINE_TOOLS_VERSION}"}
rm /tmp/tools.zip

export PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/${PROVISIONING_CMDLINE_TOOLS_VERSION}/bin"
( yes || true ) | sdkmanager --sdk_root="${ANDROID_HOME}" --licenses

if [ -n "${PROVISIONING_BUILD_TOOLS}" ]; then
  sdkmanager --sdk_root="${ANDROID_HOME}" "build-tools;${PROVISIONING_BUILD_TOOLS}"
fi
if [ -n "${PROVISIONING_CMAKE}" ]; then
  sdkmanager --sdk_root="${ANDROID_HOME}" "cmake;${PROVISIONING_CMAKE}"
fi
if [ -n "${PROVISIONING_NDK}" ]; then
  sdkmanager --sdk_root="${ANDROID_HOME}" "ndk;${PROVISIONING_NDK}"
fi
if [ -n "${PROVISIONING_PLATFORM}" ]; then
  sdkmanager --sdk_root="${ANDROID_HOME}" "platforms;${PROVISIONING_PLATFORM}"
fi
if [ -n "${PROVISIONING_PLATFORM_TOOLS}" ]; then
  sdkmanager --sdk_root="${ANDROID_HOME}" "platform-tools;${PROVISIONING_PLATFORM_TOOLS}"
fi
if [ -n "${PROVISIONING_TOOLS}" ]; then
  sdkmanager --sdk_root="${ANDROID_HOME}" "tools;${PROVISIONING_TOOLS}"
fi

git clone --recurse-submodules -b "${APP_TAG}" -- "${APP_REPOSITORY}" "${BUILD_REPO_DIR}"
cd "${BUILD_REPO_DIR}"
test "$( git rev-parse HEAD )" = "${APP_COMMIT}"

if [ "${VERIFY_GRADLE_WRAPPER}" = yes ]; then
  git clone https://github.com/obfusk/gradle-wrapper-verify /tmp/gradle-wrapper-verify
  ( shopt -s globstar; /tmp/gradle-wrapper-verify/gradle-wrapper-verify ./**/gradle-wrapper.jar )
fi

# FIXME: do more than just list these
find . -iname '*.jar' -o -iname '*.aar' | sort
