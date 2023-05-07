BUILDDIR := $(shell pwd)

O := $(BUILDDIR)/output

.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS = -e

.NOTPARALLEL:
.PHONY: build

build:
	python3 -m pip install --user build twine
	python3 -m build --outdir $(O)

venv:
	python3 -m venv $(BUILDDIR)/.venv
	. $(BUILDDIR)/.venv/bin/activate

install: venv
	pip install -e .

install-dev: install
	pip install .[lint,format,audit,tests]

uninstall:
	rm -rfv $(BUILDDIR)/.venv

clean:
	rm -rfv $(O)
