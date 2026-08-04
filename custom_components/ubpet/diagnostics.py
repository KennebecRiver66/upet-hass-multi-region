from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACTED = "REDACTED"
REDACT_KEYS = {
    "accessToken",
    "access_token",
    "account",
    "APP_KEY",
    "app_key",
    "appKey",
    "authorization",
    "baseWeight",
    "catInfoId",
    "clientId",
    "device_id",
    "deviceId",
    "icon",
    "eventTime",
    "last_poo",
    "last_pee",
    "lastWeigthTimestamp",
    "mqttPassword",
    "mqtt_password",
    "mqttUserName",
    "mqtt_username",
    "nickname",
    "password",
    "pubTopic",
    "refreshToken",
    "refresh_token",
    "subTopic",
    "subWeight",
    "token",
    "x-ubt-sign",
    "userEmail",
    "userId",
    "userImage",
    "userName",
    "userPhone",
    "user_id",
    "weight",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            "data_keys": sorted(str(key) for key in entry.data),
            "option_keys": sorted(str(key) for key in entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "data_summary": _diagnostic_data_summary(coordinator.data or {}),
    }


def _diagnostic_data_summary(data: Any) -> dict[str, Any]:
    """Return structural diagnostics without copying user or device values."""
    if not isinstance(data, dict):
        return {"data_type": type(data).__name__}

    devices = data.get("devices")
    cats = data.get("cats")
    device_items = (
        [item for item in devices.values() if isinstance(item, dict)]
        if isinstance(devices, dict)
        else []
    )
    cat_items = [item for item in cats if isinstance(item, dict)] if isinstance(cats, list) else []
    return {
        "top_level_keys": sorted(str(key) for key in data),
        "device_count": len(device_items),
        "cat_count": len(cat_items),
        "device_section_keys": sorted(
            {
                str(key)
                for device in device_items
                for key in device
            }
        ),
        "record_counts": [
            {
                "cat_records": len(device.get("cat_records", []))
                if isinstance(device.get("cat_records"), list)
                else None,
                "device_records": len(device.get("device_records", []))
                if isinstance(device.get("device_records"), list)
                else None,
            }
            for device in device_items
        ],
        "cat_field_keys": sorted(
            {
                str(key)
                for cat in cat_items
                for key in cat
            }
        ),
    }


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if key in REDACT_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
