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
    "clientId",
    "device_id",
    "deviceId",
    "icon",
    "mqttPassword",
    "mqtt_password",
    "mqttUserName",
    "mqtt_username",
    "password",
    "pubTopic",
    "refreshToken",
    "refresh_token",
    "subTopic",
    "token",
    "x-ubt-sign",
    "userEmail",
    "userImage",
    "userName",
    "userPhone",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": _redact(
            {
                "title": entry.title,
                "data": dict(entry.data),
                "options": dict(entry.options),
            }
        ),
        "last_update_success": coordinator.last_update_success,
        "data": _redact(coordinator.data or {}),
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
