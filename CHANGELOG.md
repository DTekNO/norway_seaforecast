# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (`YYYY.M.patch`).

## [2026.6.1] - 2026-06-16

### Added
- **Met.no Ocean Forecast data** — sensors are now augmented with data from the [Met.no Ocean Forecast API](https://api.met.no/weatherapi/oceanforecast/2.0/documentation), supplementing the existing Havvarsel data source
- **CF standard name variable mapping** — variables are now also identified by Climate and Forecast (CF) standard names for improved interoperability
- **User-Agent** — API requests now include a properly formed `User-Agent` header with contact URL, complying with Met.no API requirements

### Fixed
- Unique ID migration logic improved to handle conflicts and stale entity registrations cleanly when merging data sources

---

## [2026.5.2] - 2026-05-11

### Fixed
- LICENSE file is now included in the ZIP release asset
- Removed redundant legacy workflow file

---

## [2026.5.1] - 2026-05-11

### Added
- New logo assets in both PNG and SVG formats
- MIT License added to the repository

### Changed
- Replaced Havvarsel brand assets with Norway Seaforecast branding
- Removed migration guide link from Quick Start Guide

---

## [2026.3.2] - 2026-03-09

### Changed
- Minimum supported Home Assistant version set to **2026.3.0** (moved to `hacs.json` for correct enforcement)

---

## [2026.3.1] - 2026-03-09

### Added
- Brand assets (icons and logos) included directly in the custom component folder for HA brand registry compatibility

---

## [2026.02.1] - 2026-02-12

### Summary
This is a major rewrite. The integration has been completely rebuilt as a native Home Assistant custom integration (no longer AppDaemon-based), and renamed from **Havvarsel** to **Norway Seaforecast**.

### Added
- **Native HA custom integration** — full config flow UI setup via Settings → Devices & Services; no YAML or AppDaemon required
- **Multi-variable sensor support** — select one or more sea forecast variables (e.g. temperature, salinity, current speed) during setup; each becomes its own sensor entity
- **Dynamic unit mapping** — units are read from the API metadata and mapped to HA unit constants (`°C`, `m`, `m/s`); unknown units are passed through as-is
- **Coordinator-based polling** — data is fetched every 10 minutes via a shared `DataUpdateCoordinator`
- **Automated release workflow** — GitHub Actions workflow for manifest version updates and ZIP asset creation

### Changed
- **Renamed**: domain changed from `havvarsel` to `norway_seaforecast`
- Repository reorganised; README and Quick Start Guide rewritten

### Migration
Existing Havvarsel (AppDaemon) setups must be removed and re-added as the new integration. See the [Quick Start Guide](QUICKSTART.md) for setup instructions.

---

## [2025.05.1] - 2025-05-21

### Changed
- Integration added to the HACS default repository list — a custom repository entry in HACS is no longer needed

---

## [2025.02.2] - 2025-02-17

### Changed
- Documentation updates and README improvements

---

## [2025.02.1] - 2025-02-14

### Added
- Status badges added to README

### Changed
- Documentation updates and corrections

---

## [2025.02] - 2025-02-14

### Added
- Initial release — AppDaemon-based integration fetching sea temperature and forecast data from the Havvarsel API
- HACS support with validation workflow
