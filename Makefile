SHELL      := /bin/bash
PYTHON     ?= python3

SH_SCRIPTS := scripts/*.sh .scripts/*.sh
PY_SCRIPTS := scripts/*.py .scripts/*.py scripts/lint-{logs,recipes}

export PYTHONWARNINGS := default

.PHONY: all test doctest lint lint-recipes lint-scripts lint-logs
.PHONY: check-commandlinetools clean cleanup

all:

test: doctest lint

doctest:
	$(PYTHON) -m doctest $(PY_SCRIPTS)

lint: lint-recipes lint-scripts

lint-recipes:
	PYTHONWARNINGS= scripts/lint-recipes recipes/*.yml

lint-scripts:
	shellcheck $(SH_SCRIPTS)
	flake8 $(PY_SCRIPTS)
	pylint $(PY_SCRIPTS)
	for script in $(PY_SCRIPTS); do mypy --strict --disallow-any-unimported "$$script"; done

lint-logs:
	PYTHONWARNINGS= scripts/lint-logs index.json logs/*.json

clean: cleanup

cleanup:
	find -name '*~' -delete -print
	rm -fr scripts/__pycache__/ .scripts/__pycache__/ .mypy_cache/
