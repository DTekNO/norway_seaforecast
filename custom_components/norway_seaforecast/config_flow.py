"""Config flow for Norway Seaforecast integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import NorwaySeaforecastApiClient
from .const import (
    CONF_DEPTH,
    CONF_SENSOR_NAME,
    CONF_VARIABLES,
    DEFAULT_DEPTH,
    DEFAULT_SENSOR_NAME,
    DEFAULT_VARIABLES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSOR_NAME, default=DEFAULT_SENSOR_NAME): cv.string,
        vol.Required(CONF_LONGITUDE): cv.longitude,
        vol.Required(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_DEPTH, default=DEFAULT_DEPTH): cv.positive_int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    api = NorwaySeaforecastApiClient(
        session=session,
        longitude=data[CONF_LONGITUDE],
        latitude=data[CONF_LATITUDE],
        depth=data.get(CONF_DEPTH, DEFAULT_DEPTH),
    )

    # Try to fetch data to determine the nearest grid point.
    # This is optional: if the request fails we'll fall back to the
    # original user-provided coordinates so the flow does not crash.
    nearest = None
    try:
        resp = await api.async_get_temperature_data()
        # The coordinator's parsed response includes nearest_grid_lon/lat
        nearest_lon = resp.get("nearest_grid_lon")
        nearest_lat = resp.get("nearest_grid_lat")
        if nearest_lon is not None and nearest_lat is not None:
            nearest = (nearest_lat, nearest_lon)
    except Exception:  # Don't abort the flow on API errors; fallback below
        _LOGGER.debug("Could not determine nearest grid point; using provided coords", exc_info=True)

    # Return info that you want to store in the config entry. Include nearest grid if available.
    return {
        "title": data[CONF_SENSOR_NAME],
        "nearest_grid": nearest,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Norway Seaforecast."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._available_variables: dict[str, str] = {}  # {var_name: description}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        # Build the form schema dynamically so we can default to HA's home
        # location (self.hass.config.latitude / longitude).
        try:
            default_lat = float(self.hass.config.latitude)
        except Exception:
            default_lat = None

        try:
            default_lon = float(self.hass.config.longitude)
        except Exception:
            default_lon = None

        # Use HA's location name as default sensor name
        default_name = self.hass.config.location_name or DEFAULT_SENSOR_NAME

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_NAME, default=default_name): cv.string,
                vol.Required(CONF_LONGITUDE, default=default_lon): cv.longitude,
                vol.Required(CONF_LATITUDE, default=default_lat): cv.latitude,
                vol.Optional(CONF_DEPTH, default=DEFAULT_DEPTH): cv.positive_int,
            }
        )

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "cannot_connect"
            else:
                # Derive a stable slug from the sensor name for deterministic entity ids
                # e.g. "Nordnes Sea Temperature" -> "nordnes_sea_temperature"
                def _slugify(name: str) -> str:
                    import re

                    s = name.strip().lower()
                    s = re.sub(r"\s+", "_", s)
                    s = re.sub(r"[^a-z0-9_\-]", "", s)
                    s = re.sub(r"_+", "_", s)
                    return s

                slug = _slugify(user_input.get(CONF_SENSOR_NAME, DEFAULT_SENSOR_NAME))

                # Use nearest grid point if validate_input found one, otherwise use provided coords
                nearest = info.get("nearest_grid")
                if nearest:
                    # nearest is a tuple (lat, lon)
                    store_lat, store_lon = nearest[0], nearest[1]
                else:
                    store_lat = user_input[CONF_LATITUDE]
                    store_lon = user_input[CONF_LONGITUDE]

                # Create a unique ID based on the stored (effective) location and depth
                unique_id = f"{store_lat}_{store_lon}_{user_input.get(CONF_DEPTH, DEFAULT_DEPTH)}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Store data - no variable selection needed, will create all sensors
                self._data = {
                    **user_input,
                    "slug": slug,
                    CONF_LATITUDE: store_lat,
                    CONF_LONGITUDE: store_lon,
                }
                
                # Notification about nearest grid point
                if nearest:
                    try:
                        provided_lat = float(user_input.get(CONF_LATITUDE))
                        provided_lon = float(user_input.get(CONF_LONGITUDE))
                        
                        # Calculate distance to see if grid point differs
                        lat_diff = abs(float(store_lat) - provided_lat)
                        lon_diff = abs(float(store_lon) - provided_lon)
                        coords_differ = (lat_diff > 0.001) or (lon_diff > 0.001)
                        
                        if coords_differ:
                            msg = (
                                f"Norway Seaforecast adjusted coordinates for '{user_input.get(CONF_SENSOR_NAME)}':\n\n"
                                f"Requested: {provided_lat:.4f}°, {provided_lon:.4f}°\n"
                                f"Nearest grid point: {store_lat:.4f}°, {store_lon:.4f}°\n\n"
                                "The integration will use the nearest available grid point with data."
                            )
                            _LOGGER.info(
                                "Norway Seaforecast: Using nearest grid point (%.4f, %.4f) instead of requested (%.4f, %.4f)",
                                store_lat, store_lon, provided_lat, provided_lon
                            )
                        else:
                            msg = (
                                f"Norway Seaforecast configured for '{user_input.get(CONF_SENSOR_NAME)}':\n\n"
                                f"Grid point: {store_lat:.4f}°, {store_lon:.4f}°\n\n"
                                "Using nearest available grid point with data."
                            )
                            _LOGGER.info(
                                "Norway Seaforecast: Configured at grid point (%.4f, %.4f)",
                                store_lat, store_lon
                            )
                        
                        # Always show notification when grid point is determined
                        self.hass.async_create_task(
                            self.hass.services.async_call(
                                "persistent_notification",
                                "create",
                                {
                                    "title": "Norway Seaforecast Configuration",
                                    "message": msg,
                                    "notification_id": f"norway_seaforecast_grid_{slug}",
                                },
                            )
                        )
                    except Exception:
                        _LOGGER.debug("Failed to create grid point notification", exc_info=True)

                # Create entry immediately without variable selection step
                return self.async_create_entry(
                    title=user_input.get(CONF_SENSOR_NAME, "Norway Seaforecast"),
                    data=self._data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
