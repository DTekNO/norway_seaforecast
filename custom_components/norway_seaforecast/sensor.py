"""Sensor platform for Norway Seaforecast."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfLength, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HAVVARSEL_TO_CF_NAME, MET_OCEAN_EXCLUSIVE_VARIABLES, MET_OCEAN_VARIABLES_METADATA
from .const import CONF_SENSOR_NAME, CONF_VARIABLES, DEFAULT_SENSOR_NAME, DEFAULT_VARIABLES, DOMAIN
from .coordinator import NorwaySeaforecastDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _migrate_entity_unique_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate unique_ids from raw havvarsel variable names to CF standard names.

    Runs on every setup but only acts when an old-style unique_id is found.
    Entity history, entity_id slugs, and dashboard assignments are preserved.

    Conflict handling: if the target unique_id is already claimed by another entity
    from the same config entry (e.g. a stale met.no-only sensor from a previous
    version), that stale entity is removed first, then the source entity is renamed.
    This ensures the merged sensor can register cleanly without leaving orphans.
    """
    entity_registry = async_get_entity_registry(hass)
    # Snapshot of the registry at start: unique_id → full RegistryEntry
    uid_to_entry: dict[str, er.RegistryEntry] = {
        e.unique_id: e for e in entity_registry.entities.values()
    }
    for entity_entry in list(entity_registry.entities.values()):
        if entity_entry.config_entry_id != entry.entry_id:
            continue
        for raw_name, cf_name in HAVVARSEL_TO_CF_NAME.items():
            old_suffix = f"_{raw_name}"
            new_suffix = f"_{cf_name}"
            if (
                entity_entry.unique_id.endswith(old_suffix)
                and not entity_entry.unique_id.endswith(new_suffix)
            ):
                new_unique_id = entity_entry.unique_id[: -len(old_suffix)] + new_suffix
                if new_unique_id in uid_to_entry:
                    occupant = uid_to_entry[new_unique_id]
                    if occupant.config_entry_id == entry.entry_id:
                        # Same config entry: occupant is a stale sensor from an old design
                        # (e.g. the met.no-only sea_water_temperature entity).
                        # Remove it so the source entity can take the unique_id cleanly.
                        _LOGGER.info(
                            "Removing stale entity %s to free unique_id for %s",
                            occupant.entity_id,
                            entity_entry.entity_id,
                        )
                        entity_registry.async_remove(occupant.entity_id)
                        entity_registry.async_update_entity(
                            entity_entry.entity_id, new_unique_id=new_unique_id
                        )
                        _LOGGER.info(
                            "Migrated %s unique_id: ...%s \u2192 ...%s",
                            entity_entry.entity_id,
                            old_suffix,
                            new_suffix,
                        )
                    else:
                        # Claimed by a different config entry — don't touch the occupant;
                        # remove the now-redundant source entity instead.
                        _LOGGER.warning(
                            "Cannot migrate %s: unique_id %s already claimed by %s (different entry)",
                            entity_entry.entity_id,
                            new_unique_id,
                            occupant.entity_id,
                        )
                        entity_registry.async_remove(entity_entry.entity_id)
                else:
                    entity_registry.async_update_entity(
                        entity_entry.entity_id, new_unique_id=new_unique_id
                    )
                    _LOGGER.info(
                        "Migrated %s unique_id: ...%s \u2192 ...%s",
                        entity_entry.entity_id,
                        old_suffix,
                        new_suffix,
                    )
                break  # Only one raw_name can match per entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Norway Seaforecast sensor."""
    coordinator: NorwaySeaforecastDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Migrate any existing entities that still use raw havvarsel variable names
    # in their unique_id (e.g. "temperature") to CF standard names ("sea_water_temperature").
    # This is a one-time, seamless rename — history and entity_ids are preserved.
    _migrate_entity_unique_ids(hass, entry)

    # Fetch all available variables from API with metadata
    try:
        available_variables_dict = await coordinator.api.async_get_available_variables()
        _LOGGER.debug("Found %d available variables to create sensors for", len(available_variables_dict))
        
        # Also fetch full metadata to get standard_name for entity IDs
        metadata_dict = await coordinator.api.async_get_variables_metadata()
    except Exception:
        _LOGGER.exception("Failed to fetch available variables, using temperature only")
        available_variables_dict = {"temperature": "Sea water potential temperature"}
        metadata_dict = {}
    
    entities: list[NorwaySeaforecastVariableSensor] = []
    havvarsel_varnames: set[str] = set(available_variables_dict.keys())

    # Sensors from havvarsel — temperature enabled by default, others disabled
    for varname in havvarsel_varnames:
        sensor = NorwaySeaforecastVariableSensor(coordinator, entry, varname, metadata_dict.get(varname, []))
        if varname != "temperature":
            sensor._attr_entity_registry_enabled_default = False
        entities.append(sensor)

    # Sensors from met.no (depth=0 only) — skip any variable already covered by havvarsel
    if coordinator.met_api is not None:
        met_variables_dict = coordinator.met_api.get_available_variables()
        for varname in met_variables_dict:
            if varname in havvarsel_varnames:
                continue  # Havvarsel already covers this variable
            sensor = NorwaySeaforecastVariableSensor(
                coordinator, entry, varname, MET_OCEAN_VARIABLES_METADATA.get(varname, [])
            )
            # Wave variables are exclusive to met.no and high-value — enable by default
            if varname not in MET_OCEAN_EXCLUSIVE_VARIABLES:
                sensor._attr_entity_registry_enabled_default = False
            entities.append(sensor)

    _LOGGER.info(
        "Norway Seaforecast: created %d sensors (%d enabled by default)",
        len(entities),
        sum(1 for e in entities if getattr(e, "_attr_entity_registry_enabled_default", True))
    )

    async_add_entities(entities, False)


class NorwaySeaforecastVariableSensor(
    CoordinatorEntity[NorwaySeaforecastDataUpdateCoordinator], SensorEntity
):
    """Generic sensor for a single Norway Seaforecast variable."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"series"})

    def __init__(
        self,
        coordinator: NorwaySeaforecastDataUpdateCoordinator,
        entry: ConfigEntry,
        variable_name: str,
        metadata: list[dict[str, str]] | None = None,
    ) -> None:
        """Initialize the sensor for a variable (e.g. temperature)."""
        super().__init__(coordinator)
        self.variable_name = variable_name
        self._metadata_cache = metadata or []  # Cache metadata for entity naming

        sensor_name = entry.data.get(CONF_SENSOR_NAME, DEFAULT_SENSOR_NAME)
        slug = entry.data.get("slug") or sensor_name.replace(" ", "_").lower()

        # Unique id includes slug, entry id and variable name
        self._attr_unique_id = f"{slug}_{entry.entry_id}_{variable_name}"

        # Device is the location, entity name is the measurement type
        # Extract standard_name and long_name from metadata
        standard_name = None
        long_name = None
        for meta in self._metadata_cache:
            if isinstance(meta, dict):
                if meta.get("key") == "standard_name":
                    standard_name = meta.get("value")
                elif meta.get("key") == "long_name":
                    long_name = meta.get("value")
        
        # Use long_name for display (friendly name shown in UI)
        # Falls back to standard_name or variable_name if not available
        if long_name:
            self._attr_name = long_name
        elif standard_name:
            # If no long_name, format standard_name nicely
            self._attr_name = standard_name.replace("_", " ").title()
        else:
            # Final fallback to variable name
            self._attr_name = variable_name.replace("_", " ").title()
        
        # Store standard_name for entity_id generation (HA will slugify this)
        self._standard_name = standard_name
        
        # Cache for units to avoid repeated lookups and logging
        self._cached_units = None
        self._units_logged = False

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Norway Seaforecast {sensor_name}",
            manufacturer="IMR, Norway",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://api.havvarsel.no",
        )

        # State class for numeric measurements
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Device class will be set dynamically based on metadata (see device_class property)

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the device class based on variable type and available metadata."""
        # Only set device class if we have proper units from the API
        data = self.coordinator.data
        if not data:
            return None

        variables = data.get("variables", {})
        var = variables.get(self.variable_name)
        if not var:
            return None

        # Check metadata for units to ensure proper device class assignment
        metadata = var.get("metadata", [])
        for meta in metadata:
            if meta.get("key") == "units":
                units = meta.get("value", "").strip().lower()
                # Set TEMPERATURE device class for temperature variables from either source
                if self.variable_name == "sea_water_temperature" and units in ("celsius", "°c", "c"):
                    return SensorDeviceClass.TEMPERATURE
                break
        
        return None

    @property
    def native_value(self) -> float | None:
        """Return the current value for this variable from coordinator data."""
        data = self.coordinator.data
        if not data:
            return None

        variables = data.get("variables", {})
        var = variables.get(self.variable_name)
        if not var:
            return None

        return var.get("current")

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement for this variable based on API metadata."""
        # Return cached value if already determined
        if self._cached_units is not None or self._units_logged:
            return self._cached_units
        
        # Get units from cached metadata
        units = None
        for meta in self._metadata_cache:
            if isinstance(meta, dict) and meta.get("key") == "units":
                units = meta.get("value")
                break

        if not units:
            # No units provided
            self._units_logged = True  # Don't check again
            return None

        # Normalize and map API unit strings to HA unit constants
        u = str(units).strip().lower()

        # Common mappings
        if u in ("°c", "c", "celsius", "degc"):
            self._cached_units = UnitOfTemperature.CELSIUS
        elif u in ("m", "meter", "metre", "meters", "metres"):
            self._cached_units = UnitOfLength.METERS
        elif u in ("m/s", "m s-1", "ms-1", "meter second-1"):
            self._cached_units = UnitOfSpeed.METERS_PER_SECOND
        else:
            # Return raw units string if no mapping exists
            # This allows HA to display the units as-is from the API
            self._cached_units = str(units)
            _LOGGER.debug("Using raw units string for %s: %s", self.variable_name, units)
        
        self._units_logged = True
        return self._cached_units

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return attributes including the time series data and location info."""
        data = self.coordinator.data
        if not data:
            return None

        variables = data.get("variables", {})
        var = variables.get(self.variable_name)
        if not var:
            return None

        attrs = {
            "metadata": var.get("metadata", []),
            "series": var.get("series", []),
            "longitude": data.get("longitude"),
            "latitude": data.get("latitude"),
            "nearest_grid": data.get("nearest_grid"),
        }
        
        # Add standard_name if available for reference
        if self._standard_name:
            attrs["standard_name"] = self._standard_name

        return attrs

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None
