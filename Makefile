SHELL   := /bin/bash
PYTHON  ?= python3

export PYTHONWARNINGS := default

.PHONY: all test doctest lint lint-recipes lint-scripts lint-logs clean cleanup

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
	set -e; for l in logs/*.json; do echo "$$l"; \
	  jsonschema -o pretty -i "$$l" schemas/log.json; done

clean: cleanup

cleanup:
	find -name '*~' -delete -print
	rm -fr scripts/__pycache__/ .mypy_cache/
