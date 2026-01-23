# Migration Guide: AppDaemon to Custom Integration

## Overview

This repository has been converted from an AppDaemon app to a full Home Assistant custom integration. This document explains the changes and how to use the new integration.

## What Changed

### Removed Dependencies
- ❌ AppDaemon - No longer needed
- ❌ MQTT - Direct integration with Home Assistant
- ❌ Mosquitto Broker - Not required

### New Architecture

The integration now follows Home Assistant's best practices:

```
custom_components/norway_seaforecast/
├── __init__.py           # Integration entry point
├── manifest.json         # Integration metadata
├── const.py             # Constants and defaults
├── api.py               # API client (converted from havvarsel.py)
├── coordinator.py       # Data update coordinator
├── config_flow.py       # UI configuration
├── sensor.py            # Sensor platform
├── strings.json         # UI strings
└── translations/
    └── en.json          # English translations
```

## Key Changes in Functionality

### 1. API Client (`api.py`)
The old `havvarsel.py` AppDaemon app has been converted to `api.py`:
- ✅ Async/await pattern using `aiohttp`
- ✅ Clean separation of API logic
- ✅ Proper error handling
- ✅ No AppDaemon or MQTT dependencies

### 2. Configuration
**Old Way (AppDaemon):**
```yaml
# apps.yaml
havvarsel_nordnes:
  module: havvarsel
  class: HavvarselRest
  longitude: 5.302337
  latitude: 60.398942
  sensor_name: Nordnes sea temperature
```

**New Way (Custom Integration):**
- Configure through Home Assistant UI
- Settings → Devices & Services → Add Integration → Norway Seaforecast
- Fill in the form with your location details

### 3. Sensor Updates
**Old Way:**
- Used MQTT topics for sensor creation and updates
- Required retained messages
- Manual cleanup needed

**New Way:**
- Direct integration with Home Assistant's entity registry
- Automatic cleanup when integration is removed
- Native sensor attributes and device registry

## Installation Instructions

### For End Users

1. **Install via HACS:**
   - Add custom repository: `https://github.com/DTekNO/norway_seaforecast`
   - Search for "Norway Seaforecast"
   - Install and restart

2. **Configure:**
   - Go to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search "Norway Seaforecast"
   - Enter your location details

### For Developers

1. **Copy to custom_components:**
   ```bash
   cp -r custom_components/norway_seaforecast /config/custom_components/
   ```

2. **Restart Home Assistant**

3. **Check logs:**
   ```
   Settings → System → Logs
   Filter by "norway_seaforecast"
   ```

## Development Guide

### Testing Locally

1. **Copy integration to Home Assistant:**
   ```bash
   # On your HA system
   cd /config
   mkdir -p custom_components
   # Copy the norway_seaforecast folder here
   ```

2. **Enable debug logging:**
   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.norway_seaforecast: debug
   ```

3. **Restart and test:**
   - Restart Home Assistant
   - Add integration through UI
   - Check logs for any issues

### Code Structure Explanation

#### `__init__.py`
- Integration setup and teardown
- Creates coordinator
- Forwards setup to platforms (sensor)

#### `api.py`
- `NorwaySeaforecastApiClient` class
- Methods:
  - `async_get_temperature_data()` - Fetch current and forecast data
  - `async_get_units()` - Get unit of measurement
  - `_parse_response()` - Parse API response

#### `coordinator.py`
- `NorwaySeaforecastDataUpdateCoordinator` class
- Manages data updates every 10 minutes
- Handles errors and retries

#### `config_flow.py`
- UI configuration flow
- Validates user input
- Creates unique config entries

#### `sensor.py`
- `NorwaySeaforecastVariableSensor` class
- Displays current temperature
- Provides forecast as attributes

### Adding New Features

**Example: Add a new sensor for wave height**

1. Update `api.py` to fetch wave data
2. Add new sensor class in `sensor.py`
3. Update `PLATFORMS` in `__init__.py` if needed
4. Add new configuration options in `config_flow.py`

## Migration Path for Existing Users

If you're currently using the AppDaemon version:

1. **Before migration:**
   - Note your sensor configurations from `apps.yaml`
   - Take screenshots of your dashboard configurations

2. **Remove old setup:**
   - Uninstall AppDaemon app (optional)
   - Old MQTT sensors will become unavailable

3. **Install new integration:**
   - Follow installation instructions above
   - Recreate sensors with same locations

4. **Update dashboards:**
   - Update entity IDs in your dashboards
   - Old: `sensor.havvarsel_nordnes_sea_temperature`
   - New: `sensor.norway_seaforecast_nordnes_sea_water_potential_temperature`

## API Reference

### Norway Seaforecast (Havvarsel) API Endpoints

**Temperature Projection:**
```
GET https://api.havvarsel.no/apis/duapi/havvarsel/v2/temperatureprojection/{lon}/{lat}?depth={depth}
```

**Variables Metadata:**
```
GET https://api.havvarsel.no/apis/duapi/havvarsel/v2/variables
```

### Sensor Attributes

Each sensor provides these attributes:
- `longitude` - Your specified longitude
- `latitude` - Your specified latitude  
- `nearest_grid_lon` - Nearest grid point longitude
- `nearest_grid_lat` - Nearest grid point latitude
- `timestamp` - Time of measurement
- `forecast` - Array of forecast objects with:
  - `timestamp` - ISO format timestamp
  - `temperature` - Temperature value

## Troubleshooting

### Integration won't load
- Check Home Assistant logs
- Verify custom_components folder structure
- Ensure manifest.json is valid

### Sensor shows "Unavailable"
- Check internet connectivity
- Verify coordinates are on Norwegian coast
- Check API is accessible

### Forecast not updating
- Check update interval (10 minutes)
- Look for errors in logs
- Verify API response format hasn't changed

## Contributing

To contribute to this integration:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## Future Enhancements

Possible improvements:
- [ ] Add wave height sensors
- [ ] Add current/tide sensors
- [ ] Configurable update interval
- [ ] Support for more forecast variables
- [ ] Unit tests
- [ ] Integration tests
- [ ] Multi-language support

## Support

For issues and questions:
- GitHub Issues: https://github.com/DTekNO/norway_seaforecast/issues
- Home Assistant Community: https://community.home-assistant.io/

## License

Same as original AppDaemon version.
