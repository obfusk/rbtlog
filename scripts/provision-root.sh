#!/bin/bash
# SPDX-FileCopyrightText: 2024 FC (Fay) Stegerman <flx@obfusk.net>
# SPDX-License-Identifier: AGPL-3.0-or-later
set -xeuo pipefail

if [ -e /etc/apt ]; then
  export DEBIAN_FRONTEND=noninteractive

  if [ -n "${HTTP_PROXY:-}" ]; then
    printf 'Acquire::http::Proxy "%s";\n' "$HTTP_PROXY" >> /etc/apt/apt.conf.d/proxy
  fi
  if [ -n "${HTTPS_PROXY:-}" ]; then
    printf 'Acquire::https::Proxy "%s";\n' "$HTTPS_PROXY" >> /etc/apt/apt.conf.d/proxy
  fi

  apt-get update
  apt-get upgrade -y
  apt-get install --no-install-recommends -y adduser git wget unzip "${PROVISIONING_JDK}"

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
elif [ -e /etc/dnf ]; then
  DNF_OPTS=( -y --setopt=install_weak_deps=False )

  # FIXME: http(s) proxy

  dnf upgrade --refresh -y                # NB: sdkmanager needs which
  dnf install "${DNF_OPTS[@]}" git unzip which "${PROVISIONING_JDK}"
  dnf install "${DNF_OPTS[@]}" wget2-wget || dnf install "${DNF_OPTS[@]}" wget

  if [ -n "${PROVISIONING_EXTRA_PACKAGES}" ]; then
    readarray -d , -t extra_packages < <( printf %s "${PROVISIONING_EXTRA_PACKAGES}" )
    dnf install "${DNF_OPTS[@]}" "${extra_packages[@]}"
  fi

  alternatives --auto java                # FIXME: unneeded?

  useradd --home-dir "${BUILD_HOME_DIR}" "${BUILD_USER}"
else
  echo 'Unsupported OS: no apt or dnf' >&2
  exit 1
fi

mkdir -p /opt "${ANDROID_HOME}"
chown "${BUILD_USER}:${BUILD_USER}" /opt "${ANDROID_HOME}"
