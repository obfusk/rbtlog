#!/bin/bash
set -euo pipefail
set -x

for x in $( git log --format=%H log ); do git verify-commit "$x"; done
for x in $( git tag ); do git verify-tag "$x"; done

test 0 = "$( git diff code master | grep '^---' | grep -cvF /dev/null )"
test 0 = "$( git diff code master | grep '^+++' | grep -cv '/recipes/.*\.yml$' )"
test 0 = "$( git diff master log | grep '^---' | grep -cvF /dev/null )"
test 0 = "$( git diff master log | grep '^+++' | grep -cv '\.json$' )"
