from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "ubpet_config_flow_test"


def load_config_flow_module():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT / "custom_components" / "ubpet")]
    sys.modules[PACKAGE_NAME] = package

    api_path = ROOT / "custom_components" / "ubpet" / "api.py"
    api_spec = importlib.util.spec_from_file_location(f"{PACKAGE_NAME}.api", api_path)
    api = importlib.util.module_from_spec(api_spec)
    assert api_spec.loader is not None
    sys.modules[api_spec.name] = api
    api_spec.loader.exec_module(api)

    const = types.ModuleType(f"{PACKAGE_NAME}.const")
    const.CONF_APP_ID = "app_id"
    const.CONF_APP_KEY = "app_key"
    const.CONF_AREA_CODE = "area_code"
    const.CONF_BASE_URL = "base_url"
    const.CONF_COUNTRY = "country"
    const.CONF_DEVICE_ID = "device_id"
    const.CONF_PRODUCT = "product"
    const.DEFAULT_APP_ID = "default-app-id"
    const.DEFAULT_APP_KEY = "default-app-key"
    const.DEFAULT_AREA_CODE = "RU"
    const.DEFAULT_BASE_URL = "https://example.test"
    const.DEFAULT_PRODUCT = "default-product"
    const.DOMAIN = "ubpet"
    const.EU_BASE_URL = "https://apis-eu.example.test"
    const.RUSSIA_BASE_URL = "https://apis-ru.example.test"
    const.SUPPORTED_COUNTRIES = ("DE", "RU")
    sys.modules[const.__name__] = const

    voluptuous = types.ModuleType("voluptuous")
    sys.modules["voluptuous"] = voluptuous

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = object
    config_entries.ConfigEntry = object

    hass_const = types.ModuleType("homeassistant.const")
    hass_const.CONF_PASSWORD = "password"
    hass_const.CONF_USERNAME = "username"

    core = types.ModuleType("homeassistant.core")
    core.callback = lambda func: func
    core.HomeAssistant = object

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    selector = types.ModuleType("homeassistant.helpers.selector")
    helpers.selector = selector

    homeassistant.config_entries = config_entries
    homeassistant.const = hass_const
    homeassistant.core = core
    homeassistant.helpers = helpers
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.const"] = hass_const
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.selector"] = selector

    path = ROOT / "custom_components" / "ubpet" / "config_flow.py"
    flow_spec = importlib.util.spec_from_file_location(f"{PACKAGE_NAME}.config_flow", path)
    config_flow = importlib.util.module_from_spec(flow_spec)
    assert flow_spec.loader is not None
    sys.modules[flow_spec.name] = config_flow
    flow_spec.loader.exec_module(config_flow)
    return api, config_flow


api, config_flow = load_config_flow_module()


class ConfigFlowUnitTests(unittest.TestCase):
    def test_country_routing_uses_russian_endpoint(self):
        data = config_flow._country_connection_data(
            {"country": "ru", "username": "user@example.com", "password": "secret"}
        )

        self.assertEqual(data["country"], "RU")
        self.assertEqual(data["area_code"], "RU")
        self.assertEqual(data["base_url"], "https://apis-ru.example.test")

    def test_country_routing_uses_european_endpoint_and_country_code(self):
        data = config_flow._country_connection_data(
            {"country": "DE", "username": "user@example.com", "password": "secret"}
        )

        self.assertEqual(data["area_code"], "DE")
        self.assertEqual(data["base_url"], "https://apis-eu.example.test")

    def test_country_routing_rejects_unsupported_country(self):
        with self.assertRaises(ValueError):
            config_flow._country_connection_data(
                {"country": "US", "username": "user@example.com", "password": "secret"}
            )

    def test_error_mapping_distinguishes_validation_stages(self):
        cases = (
            (api.UbpetAuthenticationError(400, {"code": 2004}, stage="login"), "auth_failed"),
            (api.UbpetDeviceListError(503, {"code": 5001}, stage="device_list"), "device_list_failed"),
            (api.UbpetUnexpectedResponseError(200, {}, stage="login"), "unexpected_response"),
            (api.UbpetConnectionError(stage="device_list"), "cannot_connect"),
            (RuntimeError("unexpected"), "unknown"),
        )
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(config_flow._error_key_for_exception(error), expected)

    def test_successful_login_then_device_list_failure_is_not_auth_failure(self):
        captured = {}

        class FakeClient:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def login(self):
                return api.UbpetAuth(
                    token="token",
                    refresh_token=None,
                    expires_at_ms=None,
                    user_id=1,
                )

            def get_devices(self):
                raise api.UbpetDeviceListError(
                    503,
                    {"code": 5001, "message": "device service unavailable"},
                    stage="device_list",
                )

        data = {
            "username": "user@example.com",
            "password": "secret",
            "app_key": "app-key",
            "app_id": "app-id",
            "base_url": "https://example.test",
            "area_code": "RU",
            "product": "product",
            "device_id": "device-id",
        }
        with patch.object(config_flow, "UbpetClient", FakeClient):
            with self.assertRaises(api.UbpetDeviceListError) as raised:
                config_flow._validate_input(data)

        self.assertEqual(
            config_flow._error_key_for_exception(raised.exception),
            "device_list_failed",
        )
        self.assertNotEqual(
            config_flow._error_key_for_exception(raised.exception),
            "auth_failed",
        )
        self.assertEqual(captured["base_url"], "https://example.test")
        self.assertEqual(captured["area_code"], "RU")


if __name__ == "__main__":
    unittest.main()
