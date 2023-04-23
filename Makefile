BUILDDIR := $(shell pwd)

O := $(BUILDDIR)/output

.NOTPARALLEL: build venv install install-dev uninstall clean
.PHONY: .NOTPARALLEL

build:
	python -m pip install --user build twine
	python -m build --outdir $(O)

venv:
	python -m venv $(BUILDDIR)/.venv
	. $(BUILDDIR)/.venv/bin/activate

install: venv
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

uninstall:
	rm -rfv $(BUILDDIR)/.venv

clean:
	rm -rfv $(O)
