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
	PYTHON=$(PYTHON) scripts/lint-recipes recipes/*.yml

lint-scripts:
	shellcheck scripts/*.sh
	flake8 scripts/*.py
	pylint scripts/*.py
	mypy --strict --disallow-any-unimported scripts/*.py

lint-logs:
	scripts/lint-logs index.json logs/*.json

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
