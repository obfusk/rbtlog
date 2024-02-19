SHELL   := /bin/bash
PYTHON  ?= python3

export PYTHONWARNINGS := default

.PHONY: all test doctest lint lint-recipes lint-scripts lint-logs
.PHONY: check-commandlinetools clean cleanup

all:

test: doctest lint

doctest:
	$(PYTHON) -m doctest scripts/*.py

lint: lint-recipes lint-scripts

lint-recipes:
	yamllint recipes/*.yml
	set -e; for r in recipes/*.yml; do echo "$$r"; \
	  $(PYTHON) scripts/yaml2json < "$$r" \
	  | jsonschema -o pretty schemas/recipe.json; done

lint-scripts:
	shellcheck scripts/*.sh
	flake8 scripts/*.py
	pylint scripts/*.py
	mypy --strict --disallow-any-unimported scripts/*.py

lint-logs:
	jsonschema -o pretty -i index.json schemas/log-index.json
	set -e; for l in logs/*.json; do echo "$$l"; \
	  jsonschema -o pretty -i "$$l" schemas/log.json; done

check-commandlinetools:
	diff -Naur \
	  <( $(PYTHON) scripts/yaml2json < recipes/me.hackerchick.catima.yml \
	    | jq -r '.versions[-1].apks[-1].provisioning.cmdline_tools.url' \
	    | sed 's!.*/!!' ) \
	  <( curl -s https://developer.android.com/studio \
	    | grep -Eo 'commandlinetools-linux-[0-9]+_latest.zip' | head -1 )

clean: cleanup

cleanup:
	find -name '*~' -delete -print
	rm -fr scripts/__pycache__/ .mypy_cache/
