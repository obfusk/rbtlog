#!/bin/bash
set -euo pipefail
set -x

for x in $( git log --format=%H log ); do git verify-commit "$x"; done
for x in $( git tag ); do git verify-tag "$x"; done

git diff --exit-code code master ':!recipes/*.yml'
git diff --exit-code master log ':!logs/*.json' ':![i]ndex.json' ':![a]bout.json'

echo OK
