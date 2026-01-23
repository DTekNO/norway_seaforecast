# Norway Seaforecast Custom Integration for Home Assistant

This directory contains the Norway Seaforecast custom integration.

## Structure

- `__init__.py` - Integration setup and entry point
- `manifest.json` - Integration metadata
- `const.py` - Constants and configuration
- `api.py` - API client for Norway Seaforecast service
- `coordinator.py` - Data update coordinator
- `config_flow.py` - UI configuration flow
- `sensor.py` - Sensor platform implementation
- `strings.json` - UI strings
- `translations/` - Localization files

## Development

To test this integration:

1. Copy the `custom_components/norway_seaforecast` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through the UI: Settings → Devices & Services → Add Integration → Norway Seaforecast

## API Reference

The integration uses the Norway Seaforecast (Havvarsel) API from the Norwegian Institute for Marine Research:
- Base URL: https://api.havvarsel.no/apis/duapi/havvarsel/v2/
- Data projection: `/dataprojection/{variables}/{lon}/{lat}?depth={depth}`
- Variables metadata: `/dataprojectionvariables`
- Temperature projection (legacy): `/temperatureprojection/{lon}/{lat}?depth={depth}`

## Features

- Async API client with aiohttp
- DataUpdateCoordinator for efficient updates
- Config flow for UI-based setup
- Proper device and entity registry integration
- Time series data as sensor attributes
- Support for 13 different oceanographic variables
- Dynamic sensor enabling/disabling
- Only fetches data for enabled sensors (efficient API usage)
- CF Standard Names for entity IDs
