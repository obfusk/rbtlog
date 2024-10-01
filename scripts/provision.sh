#!/bin/bash
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later
set -xeuo pipefail

retry() {
  # Usage: retry TIMES COMMAND...
  local i n="$1"
  shift
  for (( i = 1; i <= n; ++i )); do
    if "$@"; then
      return 0
    elif (( i < n )); then
      echo retrying...
      sleep 1
    fi
  done
  return 1
}

mkdir -p "${ANDROID_HOME}"/cmdline-tools

wget -q -O /tmp/tools.zip -- "${PROVISIONING_CMDLINE_TOOLS_URL}"
sha256sum -c <<< "${PROVISIONING_CMDLINE_TOOLS_SHA256}  /tmp/tools.zip"
unzip -q -d "${ANDROID_HOME}"/cmdline-tools /tmp/tools.zip
mv "${ANDROID_HOME}"/cmdline-tools/{cmdline-tools,"${PROVISIONING_CMDLINE_TOOLS_VERSION}"}
rm /tmp/tools.zip

export PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/${PROVISIONING_CMDLINE_TOOLS_VERSION}/bin"
( yes || true ) | sdkmanager --sdk_root="${ANDROID_HOME}" --licenses > /dev/null

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

if [ "${VERIFY_GIT}" = yes ]; then
  for k in fetch receive transfer; do
    git config --global "$k".fsckObjects true
  done
fi

if [ "${WINDOWS_LIKE}" = yes ]; then
  clone_opts=( -c core.symlinks=false )
else
  clone_opts=()
fi

if [ "${APP_TAG}" != :commit: ]; then
  clone_opts+=( -b "${APP_TAG}" )
fi

retry 5 git clone "${clone_opts[@]}" -- "${APP_REPOSITORY}" "${BUILD_REPO_DIR}"
cd "${BUILD_REPO_DIR}"

if [ "${APP_TAG}" = :commit: ]; then
  git checkout "${APP_COMMIT}"
else
  git checkout refs/tags/"${APP_TAG}"
  test "$( git rev-parse HEAD )" = "${APP_COMMIT}"
fi

if [ -e .gitmodules ]; then
  sed -r 's!url = git@([a-z.]+):!url = https://\1/!' -i .gitmodules
  retry 5 git submodule update --init --recursive
fi

if [ "${VERIFY_GRADLE_WRAPPER}" = yes ]; then
  retry 5 git clone https://github.com/obfusk/gradle-wrapper-verify /opt/gradle-wrapper-verify
  ( shopt -s globstar; /opt/gradle-wrapper-verify/gradle-wrapper-verify ./**/gradle-wrapper.jar )
fi

# FIXME: do more than just list these
find . -iname '*.jar' -o -iname '*.aar' | sort
