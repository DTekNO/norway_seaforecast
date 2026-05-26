"""API client for Norway Seaforecast."""
from __future__ import annotations

from datetime import datetime, UTC as dtUTC
import logging
from typing import Any

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

# Met.no Ocean Forecast API
MET_OCEAN_API_URL = "https://api.met.no/weatherapi/oceanforecast/2.0/complete"

# Static metadata for met.no variables (met.no has no /variables endpoint like havvarsel)
MET_OCEAN_VARIABLES_METADATA: dict[str, list[dict[str, str]]] = {
    "sea_surface_wave_height": [
        {"key": "units", "value": "m"},
        {"key": "long_name", "value": "Sea surface wave height"},
        {"key": "standard_name", "value": "sea_surface_wave_significant_height"},
        {"key": "source", "value": "met.no"},
    ],
    "sea_surface_wave_from_direction": [
        {"key": "units", "value": "degrees"},
        {"key": "long_name", "value": "Sea surface wave from direction"},
        {"key": "standard_name", "value": "sea_surface_wave_from_direction"},
        {"key": "source", "value": "met.no"},
    ],
    "sea_water_temperature": [
        {"key": "units", "value": "Celsius"},
        {"key": "long_name", "value": "Sea water temperature (met.no)"},
        {"key": "standard_name", "value": "sea_water_temperature"},
        {"key": "source", "value": "met.no"},
    ],
    "sea_water_speed": [
        {"key": "units", "value": "meter second-1"},
        {"key": "long_name", "value": "Sea water speed (met.no)"},
        {"key": "standard_name", "value": "sea_water_speed"},
        {"key": "source", "value": "met.no"},
    ],
    "sea_water_to_direction": [
        {"key": "units", "value": "degrees"},
        {"key": "long_name", "value": "Sea water to direction (met.no)"},
        {"key": "standard_name", "value": "sea_water_to_direction"},
        {"key": "source", "value": "met.no"},
    ],
}

# Variables available from met.no but NOT from havvarsel — enabled by default at depth=0
MET_OCEAN_EXCLUSIVE_VARIABLES: frozenset[str] = frozenset({
    "sea_surface_wave_height",
    "sea_surface_wave_from_direction",
})


class NorwaySeaforecastApiClient:
    """API client for Norway Seaforecast."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        longitude: float,
        latitude: float,
        depth: int = 0,
        variables: list[str] | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._longitude = longitude
        self._latitude = latitude
        self._depth = depth
        self._variables = variables or ["temperature"]
        self._base_url = "https://api.havvarsel.no/apis/duapi/havvarsel/v2/"
        self._projection_url = f"{self._base_url}dataprojection"
        self._variables_url = f"{self._base_url}variables"
        self._dataprojection_variables_url = f"{self._base_url}dataprojectionvariables"

    async def async_get_units(self) -> str:
        """Get the unit of measurement for temperature from the API."""
        try:
            headers = {
                "User-agent": "Home Assistant",
                "Content-type": "application/json",
            }
            async with async_timeout.timeout(10):
                async with self._session.get(
                    self._variables_url, headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    variables = data.get("row", [])
                    for variable in variables:
                        if variable.get("variableName") == "temperature":
                            metadata = variable.get("metadata", [])
                            for meta in metadata:
                                if meta.get("key") == "units":
                                    return meta.get("value", "°C")
                    
                    return "°C"  # Default fallback
        except Exception as err:
            _LOGGER.error("Error fetching units: %s", err)
            return "°C"

    async def async_get_available_variables(self) -> dict[str, str]:
        """Get dict of available variables with their descriptions (long_name).
        
        Returns:
            Dict mapping variable name to description, e.g. {"temperature": "Sea water potential temperature"}
        """
        headers = {
            "User-agent": "Home Assistant",
            "Content-type": "application/json",
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(
                    self._dataprojection_variables_url, headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Response format is {"row": [{"variableName": "...", "metadata": [...], ...}, ...]}
                    if isinstance(data, dict) and "row" in data:
                        row = data["row"]
                        if isinstance(row, list):
                            variables_dict = {}
                            for item in row:
                                if not isinstance(item, dict):
                                    continue
                                    
                                var_name = item.get("variableName")
                                if not var_name or var_name == "time":  # Skip time dimension
                                    continue
                                
                                # Extract long_name from metadata
                                long_name = var_name  # Fallback
                                metadata = item.get("metadata", [])
                                if isinstance(metadata, list):
                                    for meta in metadata:
                                        if isinstance(meta, dict) and meta.get("key") == "long_name":
                                            long_name = meta.get("value", var_name)
                                            break
                                
                                variables_dict[var_name] = long_name
                            
                            if variables_dict:
                                _LOGGER.debug("Found %d available variables", len(variables_dict))
                                return variables_dict
                    
                    _LOGGER.warning("Unexpected dataprojectionvariables response format")
                    return {"temperature": "Sea water potential temperature"}  # Safe fallback
        except Exception as err:
            _LOGGER.error("Error fetching available variables: %s", err)
            return {"temperature": "Sea water potential temperature"}  # Safe fallback

    async def async_get_variables_metadata(self) -> dict[str, list[dict[str, str]]]:
        """Get full metadata for all variables from the /dataprojectionvariables endpoint.
        
        Returns:
            Dict mapping variable name to its metadata array, e.g. 
            {"temperature": [{"key": "units", "value": "Celsius"}, ...]}
        """
        headers = {
            "User-agent": "Home Assistant",
            "Content-type": "application/json",
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(
                    self._dataprojection_variables_url, headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Response format is {"row": [{"variableName": "...", "metadata": [...], ...}, ...]}
                    if isinstance(data, dict) and "row" in data:
                        row = data["row"]
                        if isinstance(row, list):
                            metadata_dict = {}
                            for item in row:
                                if not isinstance(item, dict):
                                    continue
                                    
                                var_name = item.get("variableName")
                                if not var_name or var_name == "time":
                                    continue
                                
                                metadata = item.get("metadata", [])
                                metadata_dict[var_name] = metadata
                            
                            _LOGGER.debug("Retrieved metadata for %d variables", len(metadata_dict))
                            return metadata_dict
                    
                    _LOGGER.warning("Unexpected dataprojectionvariables response format when fetching metadata")
                    return {}
        except Exception as err:
            _LOGGER.error("Error fetching variables metadata: %s", err)
            return {}

    async def async_get_projection(self) -> dict[str, Any]:
        """Fetch full projection data for selected variables and parse into a structured dict."""
        # First, fetch metadata for all variables to include proper units and descriptions
        _LOGGER.debug("Fetching metadata for variables...")
        variables_metadata = await self.async_get_variables_metadata()
        _LOGGER.debug("Retrieved metadata for variables: %s", list(variables_metadata.keys()))
        
        # Build URL: /dataprojection/{comma-separated-vars}/{lon}/{lat}
        vars_str = ",".join(self._variables)
        url = f"{self._projection_url}/{vars_str}/{self._longitude}/{self._latitude}"
        params = {"depth": self._depth}

        _LOGGER.info("Fetching data from: %s with params: %s", url, params)

        headers = {
            "User-agent": "Home Assistant",
            "Content-type": "application/json",
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(
                    url, params=params, headers=headers
                ) as response:
                    _LOGGER.info("API response status: %s", response.status)
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug("API response data keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
                    if isinstance(data, dict) and "data" in data:
                        _LOGGER.debug("'data' key type: %s, length: %s", type(data["data"]), len(data["data"]) if isinstance(data["data"], (list, dict)) else "N/A")
                    parsed = self._parse_projection_response(data, variables_metadata)
                    _LOGGER.info("Parsed response - found %d variables", len(parsed.get("variables", {})))
                    return parsed
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching projection data: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err, exc_info=True)
            raise

    def _parse_projection_response(self, data: dict[str, Any], variables_metadata: dict[str, list[dict[str, str]]] = None) -> dict[str, Any]:
        """Parse projection response into variables dict and meta info.
        
        Args:
            data: The API response data
            variables_metadata: Optional dict mapping variable names to their metadata arrays
        
        The /dataprojection endpoint returns a structure like:
        {
            "data": [
                {
                    "rawTime": 1760853600000,
                    "data": [
                        {"key": "temperature", "value": "11.593"},
                        {"key": "salinity", "value": "28.152"}
                    ]
                },
                ...
            ],
            "metadata": [],
            "queryPoint": {...},
            "closestGridPoint": {...},
            "closestGridPointWithData": {...},
            "depthIndex": 0,
            "depthInMeters": 0
        }
        """
        if variables_metadata is None:
            variables_metadata = {}
            
        try:
            # First, check if this is the temperatureprojection format with 'variables' array
            if "variables" in data and isinstance(data["variables"], list):
                _LOGGER.debug("Using temperatureprojection variables array format")
                return self._parse_temperatureprojection_format(data)
            
            # New format: data is an array of time points, each with nested variable data
            data_array = data.get("data", [])
            _LOGGER.debug("Parsing response with %d time points", len(data_array))
            
            # Build a dict of variables, each with their time series
            variables: dict[str, Any] = {}
            
            # Process each time point
            for time_point in data_array:
                raw_time = time_point.get("rawTime", 0)
                dt = datetime.fromtimestamp(raw_time / 1000, tz=dtUTC)
                timestamp_iso = dt.isoformat()
                
                # Each time point has a nested "data" array with key-value pairs
                nested_data = time_point.get("data", [])
                for item in nested_data:
                    var_key = item.get("key")
                    var_value = item.get("value")
                    
                    if not var_key:
                        continue
                    
                    # Initialize variable dict if first time seeing this variable
                    if var_key not in variables:
                        # Get metadata from the fetched metadata dict
                        var_metadata = variables_metadata.get(var_key, [])
                        _LOGGER.debug("Initializing variable '%s' with %d metadata entries", var_key, len(var_metadata))
                        if var_metadata:
                            # Log units if present
                            for meta in var_metadata:
                                if isinstance(meta, dict) and meta.get("key") == "units":
                                    _LOGGER.debug("Variable '%s' units: %s", var_key, meta.get("value"))
                        variables[var_key] = {
                            "metadata": var_metadata,
                            "series": [],
                            "current": None,
                            "raw_data": [],  # Store raw time/value for finding nearest
                        }
                    
                    # Add to series
                    try:
                        value_float = float(var_value) if var_value is not None else None
                    except (ValueError, TypeError):
                        value_float = None
                    
                    variables[var_key]["series"].append({
                        "timestamp": timestamp_iso,
                        "value": value_float,
                    })
                    
                    variables[var_key]["raw_data"].append({
                        "rawTime": raw_time,
                        "value": value_float,
                    })
            
            # For each variable, sort series by timestamp and find the current value (nearest to now)
            now_ms = datetime.now(dtUTC).timestamp() * 1000
            for var_key, var_info in variables.items():
                raw_data = var_info.pop("raw_data", [])  # Remove temp data
                if raw_data:
                    nearest = min(raw_data, key=lambda x: abs(x.get("rawTime", 0) - now_ms))
                    var_info["current"] = nearest.get("value")
                    _LOGGER.debug("Variable %s: %d data points, current value: %s", 
                                 var_key, len(raw_data), var_info["current"])
                
                # Sort series by timestamp for proper graphing
                var_info["series"].sort(key=lambda x: x.get("timestamp", ""))

            closest_grid = data.get(
                "closestGridPointWithData",
                {"lat": self._latitude, "lon": self._longitude},
            )

            _LOGGER.info("Successfully parsed %d variables from response", len(variables))
            
            return {
                "variables": variables,
                "nearest_grid": closest_grid,
                "nearest_grid_lon": closest_grid.get("lon") if closest_grid else self._longitude,
                "nearest_grid_lat": closest_grid.get("lat") if closest_grid else self._latitude,
                "longitude": self._longitude,
                "latitude": self._latitude,
            }

        except Exception as err:
            _LOGGER.error("Error parsing projection response: %s", err, exc_info=True)
            raise

    def _parse_temperatureprojection_format(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse temperatureprojection format with variables array."""
        variables_list = data.get("variables", [])
        _LOGGER.debug("Parsing temperatureprojection format - found %d variables in list", len(variables_list))
        variables: dict[str, Any] = {}

        for var in variables_list:
            # variableName seems to be the key used by the API
            name = var.get("variableName") or var.get("variable")
            if not name:
                _LOGGER.warning("Variable without name found in response: %s", var.keys())
                continue
                
            _LOGGER.debug("Processing variable: %s", name)
            metadata = var.get("metadata", [])
            series = []
            data_points = var.get("data", [])
            _LOGGER.debug("Variable %s has %d data points", name, len(data_points))
            
            for projection in data_points:
                raw_time = projection.get("rawTime", 0)
                dt = datetime.fromtimestamp(raw_time / 1000, tz=dtUTC)
                series.append({
                    "timestamp": dt.isoformat(),
                    "value": projection.get("value"),
                })

            # Sort series by timestamp for proper graphing
            series.sort(key=lambda x: x.get("timestamp", ""))

            # Determine nearest/current value (closest to now)
            current_value = None
            if series:
                now_ms = datetime.now(dtUTC).timestamp() * 1000
                nearest = min(var.get("data", []), key=lambda x: abs(x.get("rawTime", 0) - now_ms))
                current_value = nearest.get("value")

            variables[name] = {
                "metadata": metadata,
                "series": series,
                "current": current_value,
            }

        closest_grid = data.get(
            "closestGridPointWithData",
            {"lat": self._latitude, "lon": self._longitude},
        )

        return {
            "variables": variables,
            "nearest_grid": closest_grid,
            "nearest_grid_lon": closest_grid.get("lon") if closest_grid else self._longitude,
            "nearest_grid_lat": closest_grid.get("lat") if closest_grid else self._latitude,
            "longitude": self._longitude,
            "latitude": self._latitude,
        }

    async def async_get_temperature_data(self) -> dict[str, Any]:
        """Fetch only temperature-centric data for compatibility.

        This wraps the full projection call but returns a similar shape to the
        original async_get_temperature_data for existing callers (title/nearest
        info)."""
        projection = await self.async_get_projection()

        # Try to extract temperature info for backward compatibility
        variables = projection.get("variables", {})
        temp = variables.get("temperature") or next(iter(variables.values()), None)

        current_temp = None
        timestamp = None
        forecast = []
        if temp:
            current_temp = temp.get("current")
            # Convert series to old forecast format if present
            for entry in temp.get("series", []):
                forecast.append({"timestamp": entry.get("timestamp"), "temperature": entry.get("value")})

            if temp.get("series"):
                # Find nearest timestamp from series
                now_iso = datetime.now(dtUTC).isoformat()
                timestamp = temp.get("series")[0].get("timestamp")

        nearest_grid = projection.get("nearest_grid", {})

        return {
            "current_temperature": current_temp,
            "timestamp": timestamp,
            "longitude": projection.get("longitude"),
            "latitude": projection.get("latitude"),
            "nearest_grid_lon": nearest_grid.get("lon"),
            "nearest_grid_lat": nearest_grid.get("lat"),
            "forecast": forecast,
        }


class MetOceanApiClient:
    """API client for met.no Ocean Forecast (surface data only, no depth support)."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        longitude: float,
        latitude: float,
    ) -> None:
        """Initialize the met.no API client."""
        self._session = session
        self._longitude = longitude
        self._latitude = latitude

    def get_available_variables(self) -> dict[str, str]:
        """Return available variables with descriptions (static, no API call needed)."""
        return {
            var: next(
                (m["value"] for m in metadata if m["key"] == "long_name"),
                var.replace("_", " ").title(),
            )
            for var, metadata in MET_OCEAN_VARIABLES_METADATA.items()
        }

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch ocean forecast data from met.no and return in standard internal format."""
        headers = {"User-Agent": "Home Assistant NorwaySeaforecast/1.0"}
        params = {"lat": self._latitude, "lon": self._longitude}

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(
                    MET_OCEAN_API_URL, headers=headers, params=params
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
        except Exception as err:
            _LOGGER.error("Error fetching met.no ocean forecast: %s", err)
            raise

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse met.no oceanforecast response into standard internal format."""
        timeseries = data.get("properties", {}).get("timeseries", [])
        variables: dict[str, Any] = {}
        now = datetime.now(dtUTC).timestamp()

        for step in timeseries:
            timestamp_str = step.get("time", "")
            details = step.get("data", {}).get("instant", {}).get("details", {})

            for var_name, value in details.items():
                if var_name not in variables:
                    metadata = list(MET_OCEAN_VARIABLES_METADATA.get(var_name, []))
                    if not metadata:
                        # Unknown variable from met.no — build minimal metadata
                        metadata = [
                            {"key": "long_name", "value": var_name.replace("_", " ").title()},
                            {"key": "source", "value": "met.no"},
                        ]
                    variables[var_name] = {
                        "metadata": metadata,
                        "series": [],
                        "_raw": [],
                    }

                try:
                    value_float = float(value) if value is not None else None
                except (ValueError, TypeError):
                    value_float = None

                variables[var_name]["series"].append({
                    "timestamp": timestamp_str,
                    "value": value_float,
                })

                try:
                    dt_ts = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    ).timestamp()
                except ValueError:
                    dt_ts = 0.0
                variables[var_name]["_raw"].append({"ts": dt_ts, "value": value_float})

        # Find current value (nearest to now) for each variable
        for var_info in variables.values():
            raw = var_info.pop("_raw", [])
            if raw:
                nearest = min(raw, key=lambda x: abs(x["ts"] - now))
                var_info["current"] = nearest["value"]
            else:
                var_info["current"] = None

        geometry = data.get("geometry", {})
        coords = geometry.get("coordinates", [self._longitude, self._latitude])
        lon = coords[0] if len(coords) > 0 else self._longitude
        lat = coords[1] if len(coords) > 1 else self._latitude

        return {
            "variables": variables,
            "nearest_grid": {"lon": lon, "lat": lat},
            "nearest_grid_lon": lon,
            "nearest_grid_lat": lat,
            "longitude": self._longitude,
            "latitude": self._latitude,
        }

