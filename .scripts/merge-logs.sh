#!/bin/bash
# usage: .scripts/merge-logs.sh log second_log tag
set -euo pipefail
log="$1" second_log="$2" tag="$3"
jq '.tags[$tag]' --arg tag "$tag" < "$second_log" | .scripts/append-builds.py "$log"
