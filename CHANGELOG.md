# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2023-07-14

### Added

- Added `advanced` section in `control.yaml` with the option `persistent_tmp_dir`.
- Added documentation in [configuration.md](docs/configuration.md) for the `advanced` section.

### Changed

- Bump pymodbus to version 3.3.2
- Bump ayncio-mqtt to version 1.0.0 (the package name changed to aiomqtt)

## Fixed

- Fixed crashing Unipi Control service after reinstall/update `unipi-modbus-tools` OPKG package.
- Added `Restart=on-failure` for systemd service, in the OPKG package, to prevent unwanted crashes.
- Repair the OPKG package for the Unipi Control OS. Added the missing control files to the package. 

## [2.0.0] - 2023-06-23

### Added

- This CHANGELOG.md
- Added the developer guide to [CONTRIBUTING.md](CONTRIBUTING.md)
- Added `setuptools_scm` for automatic versioning.
- Added ruff as new linter.
- Added date and log level to unipi-control CLI output
- Added better error handling if hardware definition files are invalid

### Changed

- Changed version format to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
- Moved from legacy python package installer configuration file (setup.cfg) to [pyproject.toml](pyproject.toml)
- Updated pytest/coverage configuration
  - Save all output files e.g. `pytest.xml` in the reports folder 
- Split README.md content in separate files under [docs](docs) (Prepare for [docs.superbox.one](https://docs.superbox.one))
- Changed project structure (flat layout) to `unipi_control`, `data`, `scripts` and `tests` folder.

### Removed

- Removed superbox-utils dependencies.
- Removed old `flake8` linter.

### Fixed

- Fixed wrong logging level. Logging level from YAML configuration was not set correctly.

## [2023.7] - 2023-05-03

### Added

- New GitHub Action for deploy to Unipi Control OS.
  - Binary files to the release downloads.
  - Wheel file to the release downloads.
  - OPKG package to the release downloads (required for Unipi Control OS).
- New argument `--config` to `unipi-control` command for custom config path.
- `unipi-config-backup` command for easy creating configuration backups.
- `unipi-config-converter` to convert EVOK yaml files to Unipi Control yaml files.

### Changed

- Bump `superbox-utils` to `2023.6`.
- Updated list of supported devices.

## [2023.6] - 2023-03-19

### Added

- Added support for Modbus RTU.
- Added support for Eastron devices.

### Changed

- Update systemd service for Unipi Control OS.
- Updated packages version.
- Updated install process and README.md.

### Fixed

- Fix missing pyserial package.
