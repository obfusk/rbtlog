SHELL := /bin/bash

.PHONY: all lint lint-recipes lint-scripts

all:

lint: lint-recipes lint-scripts

lint-recipes:
	yamllint recipes/*.yml

lint-scripts:
	shellcheck scripts/*.sh
	flake8 scripts/*.py
	pylint scripts/*.py
	mypy --strict --disallow-any-unimported scripts/*.py
