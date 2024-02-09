SHELL := /bin/bash

.PHONY: all lint

all:

lint:
	yamllint recipes/*.yml
	shellcheck scripts/*.sh
	flake8 scripts/*.py
	pylint scripts/*.py
	mypy --strict --disallow-any-unimported scripts/*.py
