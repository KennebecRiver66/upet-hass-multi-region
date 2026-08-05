from __future__ import annotations

import ast
import asyncio
from enum import Enum
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "ubpet_startup_test"


def load_startup_module():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT / "custom_components" / "ubpet")]
    sys.modules[PACKAGE_NAME] = package

    api = types.ModuleType(f"{PACKAGE_NAME}.api")

    class UbpetClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    api.UbpetClient = UbpetClient
    sys.modules[api.__name__] = api

    const = types.ModuleType(f"{PACKAGE_NAME}.const")
    for name, value in {
        "CONF_AREA_CODE": "area_code",
        "CONF_APP_ID": "app_id",
        "CONF_APP_KEY": "app_key",
        "CONF_BASE_URL": "base_url",
        "CONF_DEVICE_ID": "device_id",
        "CONF_PRODUCT": "product",
        "DEFAULT_AREA_CODE": "RU",
        "DEFAULT_APP_ID": "app-id",
        "DEFAULT_APP_KEY": "app-key",
        "DEFAULT_BASE_URL": "https://example.test",
        "DEFAULT_PRODUCT": "product",
        "DOMAIN": "ubpet",
        "PLATFORMS": ("sensor",),
    }.items():
        setattr(const, name, value)
    sys.modules[const.__name__] = const

    coordinator = types.ModuleType(f"{PACKAGE_NAME}.coordinator")

    class UbpetDataUpdateCoordinator:
        instances = []

        def __init__(self, hass, client, *, entry):
            self.hass = hass
            self.client = client
            self.entry = entry
            self.first_refreshes = 0
            self.history_starts = 0
            self.mqtt_starts = 0
            self.history_cancels = 0
            self.mqtt_cancels = 0
            self.__class__.instances.append(self)

        async def async_config_entry_first_refresh(self):
            self.first_refreshes += 1

        def start_visit_history_backfill(self):
            self.history_starts += 1

        def enable_mqtt_state_polls(self):
            self.mqtt_starts += 1

        def cancel_visit_history_backfill(self):
            self.history_cancels += 1

        def cancel_mqtt_state_polls(self):
            self.mqtt_cancels += 1

    coordinator.UbpetDataUpdateCoordinator = UbpetDataUpdateCoordinator
    sys.modules[coordinator.__name__] = coordinator

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    hass_const = types.ModuleType("homeassistant.const")
    hass_const.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
    hass_const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
    core = types.ModuleType("homeassistant.core")

    class CoreState(Enum):
        starting = "STARTING"
        running = "RUNNING"

    core.CoreState = CoreState
    core.HomeAssistant = object
    core.callback = lambda func: func

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_call_later = (
        lambda hass, delay, callback: hass.async_call_later(delay, callback)
    )

    homeassistant.config_entries = config_entries
    homeassistant.const = hass_const
    homeassistant.core = core
    homeassistant.helpers = helpers
    helpers.event = event
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.const"] = hass_const
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.event"] = event

    path = ROOT / "custom_components" / "ubpet" / "__init__.py"
    spec = importlib.util.spec_from_file_location(f"{PACKAGE_NAME}.__init__", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, CoreState, UbpetDataUpdateCoordinator


startup, CoreState, FakeCoordinator = load_startup_module()


class FakeBus:
    def __init__(self):
        self.listeners = {}

    def async_listen_once(self, event, callback):
        self.listeners[event] = callback
        return lambda: self.listeners.pop(event, None)


class FakeConfigEntries:
    def __init__(self):
        self.forwarded = []

    async def async_forward_entry_setups(self, entry, platforms):
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(self, entry, platforms):
        return True


class FakeHass:
    def __init__(self, state):
        self.state = state
        self.data = {}
        self.bus = FakeBus()
        self.config_entries = FakeConfigEntries()
        self.delayed_calls = []

    def async_call_later(self, delay, callback):
        self.delayed_calls.append((delay, callback))
        return lambda: None


class FakeEntry:
    def __init__(self):
        self.entry_id = "entry-id"
        self.data = {
            "account": "user@example.com",
            "password": "secret",
            "device_id": "device-id",
        }
        self.unload_callbacks = []

    def async_on_unload(self, callback):
        self.unload_callbacks.append(callback)


class StartupSchedulingTests(unittest.TestCase):
    def setUp(self):
        FakeCoordinator.instances.clear()

    def test_mqtt_polling_waits_until_home_assistant_started(self):
        hass = FakeHass(CoreState.starting)
        entry = FakeEntry()

        asyncio.run(startup.async_setup_entry(hass, entry))

        coordinator = FakeCoordinator.instances[-1]
        self.assertEqual(coordinator.first_refreshes, 1)
        self.assertEqual(coordinator.history_starts, 0)
        self.assertEqual(coordinator.mqtt_starts, 0)
        self.assertEqual(hass.delayed_calls, [])

        hass.bus.listeners["homeassistant_started"](None)

        self.assertEqual(coordinator.history_starts, 1)
        self.assertEqual(coordinator.mqtt_starts, 0)
        self.assertEqual(len(hass.delayed_calls), 1)
        delay, callback = hass.delayed_calls[0]
        self.assertEqual(delay, startup.MQTT_POLL_START_DELAY_SECONDS)

        callback(None)

        self.assertEqual(coordinator.mqtt_starts, 1)

    def test_running_home_assistant_schedules_background_work_immediately(self):
        hass = FakeHass(CoreState.running)
        entry = FakeEntry()

        asyncio.run(startup.async_setup_entry(hass, entry))

        coordinator = FakeCoordinator.instances[-1]
        self.assertEqual(coordinator.history_starts, 1)
        self.assertEqual(coordinator.mqtt_starts, 0)
        self.assertEqual(len(hass.delayed_calls), 1)

    def test_mqtt_coroutines_use_config_entry_background_tasks(self):
        tree = ast.parse(
            (ROOT / "custom_components" / "ubpet" / "coordinator.py").read_text()
        )
        coordinator_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "UbpetDataUpdateCoordinator"
        )
        for method_name in (
            "start_visit_history_backfill",
            "_ensure_mqtt_state_poll_task",
            "_run_due_mqtt_state_polls",
        ):
            method = next(
                node
                for node in coordinator_class.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == method_name
            )
            called_attributes = {
                node.func.attr
                for node in ast.walk(method)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
            }
            self.assertIn("async_create_background_task", called_attributes)
            self.assertNotIn("async_create_task", called_attributes)


if __name__ == "__main__":
    unittest.main()
