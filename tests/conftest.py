"""Minimal stubs so the config flow imports without Home Assistant."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _module(name):
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


class AbortFlow(Exception):
    """Abort the config flow."""


class ConfigFlow:
    """Base class used by the integration config flow."""

    VERSION = 1

    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.domain = domain

    async def async_set_unique_id(self, unique_id, **kwargs):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs):
        raise AbortFlow(kwargs.get("reason"))


class ConfigEntryAuthFailed(Exception):
    pass


class ConfigEntryNotReady(Exception):
    pass


class DataUpdateCoordinator:
    """Minimal coordinator base for import-time compatibility."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger=None, name=None, **kwargs):
        self.hass = hass
        self.name = name

    def async_set_updated_data(self, data):
        pass


ha = _module("homeassistant")
config_entries = _module("homeassistant.config_entries")
config_entries.ConfigFlow = ConfigFlow
config_entries.ConfigEntry = object
config_entries.CONN_CLASS_CLOUD_POLL = "cloud_polling"
ha.config_entries = config_entries

core = _module("homeassistant.core")
core.HomeAssistant = object
ha.core = core

exceptions = _module("homeassistant.exceptions")
exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
exceptions.ConfigEntryNotReady = ConfigEntryNotReady
ha.exceptions = exceptions

helpers = _module("homeassistant.helpers")
aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
aiohttp_client.async_get_clientsession = lambda hass, *args: hass.session
helpers.aiohttp_client = aiohttp_client
update_coordinator = _module("homeassistant.helpers.update_coordinator")
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = ConfigEntryNotReady
helpers.update_coordinator = update_coordinator

aiohttp = _module("aiohttp")


class ClientError(Exception):
    pass


class ClientConnectionError(ClientError):
    pass


aiohttp.ClientError = ClientError
aiohttp.ClientConnectionError = ClientConnectionError
