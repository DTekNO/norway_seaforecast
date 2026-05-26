[![hacs][hacs-badge]][hacs-url]
[![Validate with HACS][hacs-validation-badge]][hacs-validation-url]
[![release][release-badge]][release-url]
![Maintenance][maintenance-badge]
![downloads][downloads-badge]

# Norway Seaforecast Custom Integration

Norway Seaforecast is a Home Assistant custom integration providing oceanographic data for locations along the Norwegian coast.

Data is sourced from two complementary APIs:

- **[havvarsel.no](https://api.havvarsel.no)** (Norwegian Institute of Marine Research) — ocean currents, temperature and salinity at **configurable depth** (0–bottom)
- **[api.met.no](https://api.met.no/weatherapi/oceanforecast/2.0/)** (Norwegian Meteorological Institute) — **wave height and wave direction** (surface only)

Both APIs are queried concurrently. If one is temporarily unavailable, sensors from the other continue to update. Wave data is only available at depth = 0.

## Installation

### Installation with HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Search for "Norway Seaforecast"
4. Click "Download"
5. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/norway_seaforecast` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

After installation, add the integration through the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Norway Seaforecast"
4. Fill in the configuration:
   - **Sensor Name**: A descriptive name for your location (e.g., `Home` or `Nordnes`)
   - **Longitude**: Decimal longitude (e.g., `5.302337`)
   - **Latitude**: Decimal latitude (e.g., `60.398942`)
   - **Depth**: Depth in metres (default: `0` for surface). Use `0` to also get wave data from met.no.

You can add multiple locations by repeating the process.

## Available Sensors

Entity IDs below use the example sensor name **Home** (slug: `home`). Replace `home` with the slug of your chosen sensor name.

### Surface sensors — depth = 0 (havvarsel.no + met.no)

These sensors are created when **Depth = 0**. The two wave sensors are **enabled by default**; all others are disabled by default and can be enabled individually.

| Entity ID | Variable | Unit | Source | Default |
|---|---|---|---|---|
| `sensor.norway_seaforecast_home_sea_water_potential_temperature` | Sea water potential temperature | °C | havvarsel.no | ✅ enabled |
| `sensor.norway_seaforecast_home_sea_surface_wave_height` | Sea surface wave height | m | met.no | ✅ enabled |
| `sensor.norway_seaforecast_home_sea_surface_wave_from_direction` | Sea surface wave from direction | ° | met.no | ✅ enabled |
| `sensor.norway_seaforecast_home_sea_surface_height_above_geoid` | Sea surface height above geoid (tidal/surge) | m | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_sea_water_salinity` | Sea water salinity | PSU | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_sea_water_eastward_velocity` | Sea water eastward velocity | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_sea_water_northward_velocity` | Sea water northward velocity | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_sea_water_z_velocity` | Sea water vertical velocity | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_sea_water_speed` | Sea water speed | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_sea_water_to_direction` | Sea water to direction | rad | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_surface_u_wind_component` | Surface u-wind component (model forcing) | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_surface_v_wind_component` | Surface v-wind component (model forcing) | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_wind_speed` | Wind speed (model forcing) | m/s | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_wind_to_direction` | Wind to direction (model forcing) | rad | havvarsel.no | disabled |
| `sensor.norway_seaforecast_home_ocean_vertical_salt_diffusivity` | Ocean vertical salt diffusivity | m²/s | havvarsel.no | disabled |

> **Note:** The wind variables (`Uwind_eastward`, `Vwind_northward`, `wind_direction`, `wind_length`) are the atmospheric forcing input used by the ocean model — they are not an independent weather forecast. Use a dedicated weather integration for wind.

> **Note:** `sea_surface_height_above_geoid` (`zeta`) is the slow tidal rise/fall signal (±1–2 m over hours), not wave height.

### Depth sensors — depth > 0 (havvarsel.no only)

When **Depth > 0**, the met.no API is not used (it provides surface data only) and wave sensors are not created.

The same sensors as above are available, but `temperature`, `salinity`, `u_eastward`, `v_northward`, `w`, `current_direction`, and `current_length` reflect conditions at the configured depth. The surface-only variables (`zeta`, `Uwind_eastward`, `Vwind_northward`, `wind_direction`, `wind_length`) are unaffected by depth.

### Fallback behaviour

If **havvarsel.no is down**: all havvarsel sensors show unavailable; wave sensors continue updating from met.no.

If **met.no is down**: wave sensors show unavailable; all havvarsel sensors continue updating.

If **both are down**: all sensors show unavailable; the coordinator retries on the next update cycle (every 10 minutes).

## Use

Each sensor provides:

- **Current value**: The data point nearest to now
- **`series` attribute**: Full time series (list of `{timestamp, value}`) for charting
- **`metadata` attribute**: Variable information (units, standard names, source API)
- **`nearest_grid` attribute**: The actual grid point used by havvarsel.no

### Example view configuration

![example_view.png](img/example_view.png)

To plot the `series` attribute as a chart, install the [ApexCharts card](https://github.com/RomRider/apexcharts-card).

```yaml
views:
  - type: sections
    max_columns: 2
    title: Oceanographic data
    path: oceanographic-data
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Home
            heading_style: title
          - graph: line
            type: sensor
            entity: sensor.norway_seaforecast_home_sea_water_potential_temperature
            detail: 1
            icon: mdi:thermometer-water
            grid_options:
              columns: full
            name: Sea temperature
          - graph: line
            type: sensor
            entity: sensor.norway_seaforecast_home_sea_surface_wave_height
            detail: 1
            icon: mdi:waves
            grid_options:
              columns: full
            name: Wave height
          - type: custom:apexcharts-card
            grid_options:
              columns: full
              rows: 4
            graph_span: 72h
            span:
              offset: +60h
            now:
              show: true
              label: Now
            header:
              show: true
              show_states: true
            apex_config:
              stroke:
                curve: smooth
            yaxis:
              - id: temp
                decimals: 1
              - id: wave
                decimals: 2
                opposite: true
            series:
              - entity: sensor.norway_seaforecast_home_sea_water_potential_temperature
                yaxis_id: temp
                name: Temperature (°C)
                data_generator: |
                  return entity.attributes.series.map((entry) => {
                    return [new Date(entry.timestamp).getTime(), entry.value];
                  });
              - entity: sensor.norway_seaforecast_home_sea_surface_wave_height
                yaxis_id: wave
                name: Wave height (m)
                data_generator: |
                  return entity.attributes.series.map((entry) => {
                    return [new Date(entry.timestamp).getTime(), entry.value];
                  });
      - type: grid
        cards:
          - type: heading
            heading: Map
            heading_style: title
          - type: map
            entities:
              - entity: sensor.norway_seaforecast_home_sea_water_potential_temperature
            theme_mode: auto
            grid_options:
              columns: full
              rows: 8
```

## Removing the Integration

Go to **Settings** → **Devices & Services** → **Norway Seaforecast** → select the device → **Delete**.

<!-- Badge definitions -->
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://github.com/DTekNO/norway_seaforecast
[hacs-validation-badge]: https://github.com/DTekNO/norway_seaforecast/actions/workflows/validate.yaml/badge.svg
[hacs-validation-url]: https://github.com/DTekNO/norway_seaforecast/actions/workflows/validate.yaml
[maintenance-badge]: https://img.shields.io/maintenance/yes/2026.svg
[release-badge]: https://img.shields.io/github/release/DTekNO/norway_seaforecast.svg
[release-url]: https://github.com/DTekNO/norway_seaforecast/releases
[downloads-badge]: https://img.shields.io/github/downloads/DTekNO/norway_seaforecast/total
