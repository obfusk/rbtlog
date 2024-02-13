SHELL   := /bin/bash
PYTHON  ?= python3

export PYTHONWARNINGS := default

.PHONY: all test doctest lint lint-recipes lint-scripts clean cleanup

all:

test: doctest lint

doctest:
	$(PYTHON) -m doctest scripts/*.py

lint: lint-recipes lint-scripts

lint-recipes:
	yamllint recipes/*.yml

lint-scripts:
	shellcheck scripts/*.sh
	flake8 scripts/*.py
	pylint scripts/*.py
	mypy --strict --disallow-any-unimported scripts/*.py

clean: cleanup

cleanup:
	find -name '*~' -delete -print
	rm -fr scripts/__pycache__/ .mypy_cache/
