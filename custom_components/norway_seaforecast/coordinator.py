"""DataUpdateCoordinator for Norway Seaforecast."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NorwaySeaforecastApiClient
from .const import (
    CONF_DEPTH,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    DEFAULT_DEPTH,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class NorwaySeaforecastDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Norway Seaforecast data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        # Create API client without variables initially
        self.api = NorwaySeaforecastApiClient(
            session=async_get_clientsession(hass),
            longitude=entry.data[CONF_LONGITUDE],
            latitude=entry.data[CONF_LATITUDE],
            depth=entry.data.get(CONF_DEPTH, DEFAULT_DEPTH),
            variables=["temperature"],  # Default, will be updated dynamically
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def _get_enabled_variables(self) -> list[str]:
        """Get list of enabled variables from entity registry."""
        entity_registry = async_get_entity_registry(self.hass)
        enabled_vars = []
        
        # Look for all norway_seaforecast entities for this config entry
        for entity_id, entry in entity_registry.entities.items():
            if entry.config_entry_id == self.entry.entry_id and entry.domain == "sensor":
                # Check if entity is enabled
                if not entry.disabled:
                    # Extract variable name from unique_id: format is "slug_entryid_varname"
                    parts = entry.unique_id.split("_")
                    if len(parts) >= 3:
                        var_name = "_".join(parts[2:])  # Handle variable names with underscores
                        enabled_vars.append(var_name)
        
        # Always include temperature as fallback
        if not enabled_vars or "temperature" not in enabled_vars:
            enabled_vars.append("temperature")
        
        _LOGGER.debug("Enabled variables for data fetch: %s", ", ".join(enabled_vars))
        return enabled_vars

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API for only enabled sensors."""
        try:
            # Update API client with currently enabled variables
            enabled_vars = self._get_enabled_variables()
            self.api._variables = enabled_vars
            
            data = await self.api.async_get_projection()
            # data: { 'variables': { varname: {...}}, 'nearest_grid': {...}, 'longitude':..., 'latitude':... }
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
