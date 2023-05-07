# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

### Added

- This CHANGELOG.md
- Added the developer guide to [CONTRIBUTING.md](CONTRIBUTING.md)

### Changed

- Moved from legacy python package installer configuration file (setup.cfg) to [pyproject.toml](pyproject.toml)
- Updated pytest/coverage configuration
  - Save all output files e.g. `pytest.xml` in the reports folder 
- Split README.md content in separate files under [docs](docs) (Prepare for [docs.superbox.one](https://docs.superbox.one))

## [2023.7] - 2023-07-04

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
