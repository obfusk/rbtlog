#!/bin/bash
set -e
export LC_COLLATE=C.UTF-8
url="$1"  # v2 index url
if [ "${url:0:8}" = https:// ] || [ "${url:0:7}" = http:// ]; then
  cmd=( curl -sL -- "$url" )
else
  cmd=( cat -- "$1" )
fi
echo "Packages not in index:"
# shellcheck disable=SC2012
diff -Naur <( "${cmd[@]}" | jq -r '.packages|keys[]' | sort ) \
           <( cd recipes && ls -- *.yml | sed 's!\.yml$!!' ) \
           | tail -n +3 | grep ^+ | cut -c2-
