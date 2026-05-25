SHELL := /bin/bash
.PHONY: clean build test run setup

default: build

clean: ## Clean python cache files
	@rm -rf build/*

setup:
	@mkdir -p build
	@/bin/python3 -m venv .venv
	@source .venv/bin/activate && pip install --upgrade pip
	@source .venv/bin/activate && pip install '.[dev]'

build:
	@mkdir -p build
	@rm -rf build/*
	@source .venv/bin/activate && python -m build -o build -w -x

test:
	@mkdir -p build
	@source .venv/bin/activate && tox

run-monitor:
	@source .venv/bin/activate && python -m pcc.pcc_monitor /dev/ttyACM0

run-aggregator:
	@source .venv/bin/activate && python -m pcc.pcc_aggregator

run-fake:
	@source .venv/bin/activate && python -m pcc.fake_dispenser  /dev/ttyUSB1


docker-build:
	docker build -t pcc .
