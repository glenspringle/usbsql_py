SHELL := /bin/bash
.PHONY: clean build test run setup

default: build

clean: ## Clean python cache files
	@rm -rf build/*

setup:
	@mkdir -p build
	@python -m venv .venv
	@source .venv/bin/activate && pip install --upgrade pip
	@source .venv/bin/activate && pip install '.[dev]'

build:
	@mkdir -p build
	@rm -rf build/*
	@source .venv/bin/activate && python -m build -o build -w -x

test:
	@mkdir -p build
	@source .venv/bin/activate && tox

run:
	@source .venv/bin/activate && python -m proj_name /dev/ttyACM0
