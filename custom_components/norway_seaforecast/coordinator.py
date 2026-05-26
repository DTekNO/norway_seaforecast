"""DataUpdateCoordinator for Norway Seaforecast."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MetOceanApiClient, NorwaySeaforecastApiClient, CF_TO_HAVVARSEL_NAME, MET_OCEAN_EXCLUSIVE_VARIABLES
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
        depth = entry.data.get(CONF_DEPTH, DEFAULT_DEPTH)

        self.api = NorwaySeaforecastApiClient(
            session=async_get_clientsession(hass),
            longitude=entry.data[CONF_LONGITUDE],
            latitude=entry.data[CONF_LATITUDE],
            depth=depth,
            variables=["temperature"],  # Default, updated dynamically
        )

        # met.no only supports surface data — only create client when depth == 0
        if depth == 0:
            self.met_api: MetOceanApiClient | None = MetOceanApiClient(
                session=async_get_clientsession(hass),
                longitude=entry.data[CONF_LONGITUDE],
                latitude=entry.data[CONF_LATITUDE],
            )
        else:
            self.met_api = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def _get_enabled_variables(self) -> list[str]:
        """Get list of enabled havvarsel variables from entity registry.

        Entity unique IDs contain CF names; this maps them back to the raw
        havvarsel API names. Met.no-exclusive variables are skipped.
        """
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
                        cf_name = "_".join(parts[2:])  # Handle variable names with underscores
                        # Skip met.no-exclusive variables — not fetchable from havvarsel
                        if cf_name in MET_OCEAN_EXCLUSIVE_VARIABLES:
                            continue
                        # Map CF name back to havvarsel raw name; unmapped vars pass through
                        raw_name = CF_TO_HAVVARSEL_NAME.get(cf_name, cf_name)
                        enabled_vars.append(raw_name)
        
        # Always include temperature as fallback
        if not enabled_vars or "temperature" not in enabled_vars:
            enabled_vars.append("temperature")
        
        _LOGGER.debug("Enabled variables for data fetch: %s", ", ".join(enabled_vars))
        return enabled_vars

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API for only enabled sensors."""
        try:
            enabled_vars = self._get_enabled_variables()
            self.api._variables = enabled_vars

            if self.met_api is not None:
                # Fetch both APIs concurrently; handle individual failures gracefully
                havvarsel_result, met_result = await asyncio.gather(
                    self.api.async_get_projection(),
                    self.met_api.async_get_data(),
                    return_exceptions=True,
                )

                if isinstance(havvarsel_result, Exception):
                    _LOGGER.warning(
                        "havvarsel.no unavailable, using met.no data only: %s",
                        havvarsel_result,
                    )
                    havvarsel_result = None

                if isinstance(met_result, Exception):
                    _LOGGER.warning(
                        "met.no unavailable, using havvarsel data only: %s",
                        met_result,
                    )
                    met_result = None

                if havvarsel_result is None and met_result is None:
                    raise UpdateFailed(
                        "Both havvarsel.no and met.no are unavailable"
                    )

                return self._merge_data(havvarsel_result, met_result)

            # depth > 0: havvarsel only
            data = await self.api.async_get_projection()
            return data

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _merge_data(
        self,
        havvarsel_data: dict[str, Any] | None,
        met_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Merge havvarsel and met.no data.

        Havvarsel takes precedence for any overlapping variable names.
        Met.no fills in wave variables and acts as fallback when havvarsel is down.
        """
        if havvarsel_data is not None:
            merged = dict(havvarsel_data)
            merged["variables"] = dict(havvarsel_data.get("variables", {}))
        else:
            # Havvarsel down — use met.no location as base
            merged = dict(met_data)
            merged["variables"] = {}

        if met_data is not None:
            for var_name, var_info in met_data.get("variables", {}).items():
                if var_name not in merged["variables"]:
                    # Either exclusive to met.no (waves) or havvarsel is down
                    merged["variables"][var_name] = var_info
                # If already present from havvarsel, skip (havvarsel takes precedence)

        return merged
