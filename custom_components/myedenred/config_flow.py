"""Config flow for myEdenred integration."""
from __future__ import annotations

import logging
import voluptuous as vol
import async_timeout

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.myedenred import MY_EDENRED, MyEdenredAuthError, MyEdenredChallengeRequired
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

DATA_SCHEMA = vol.Schema(
    { 
        vol.Required("username"): str, 
        vol.Required("password"): str,
        vol.Required("includeTransactions"): bool,
    }
)

CHALLENGE_SCHEMA = vol.Schema({vol.Required("code"): str})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """MyEdenred config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._pending_user_input = None
        self._pending_challenge = None
        self._reauth_entry = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user interface."""
        _LOGGER.debug("Starting async_step_user...")
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input["username"].lower())
            self._abort_if_unique_id_configured()

            result = await self._authenticate(user_input)
            if isinstance(result, dict) and result.get("token"):
                _LOGGER.debug("Config is valid!")
                user_input["token"] = result["token"]
                user_input["cookies"] = result.get("cookies", {})
                return self.async_create_entry(
                    title="MyEdenred " + user_input["username"], 
                    data = user_input
                ) 
            if isinstance(result, MyEdenredChallengeRequired):
                self._pending_user_input = user_input
                self._pending_challenge = result.challenge
                return await self.async_step_challenge()
            errors = {"base": "auth"}

        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA, 
            errors=errors,
        )

    async def async_step_challenge(self, user_input=None):
        """Handle the email 2FA challenge."""
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass, True)
            async with async_timeout.timeout(10):
                api = MY_EDENRED(session, self._pending_challenge.get("cookies"))
                try:
                    result = await api.login_with_challenge(
                        self._pending_user_input["username"],
                        self._pending_user_input["password"],
                        self._pending_challenge,
                        user_input["code"],
                    )
                    data = dict(self._pending_user_input)
                    data["token"] = result["token"]
                    data["cookies"] = result.get("cookies", {})
                    if self._reauth_entry:
                        self.hass.config_entries.async_update_entry(
                            self._reauth_entry,
                            data=data,
                        )
                        await self.hass.config_entries.async_reload(
                            self._reauth_entry.entry_id
                        )
                        return self.async_abort(reason="reauth_successful")
                    return self.async_create_entry(
                        title="MyEdenred " + data["username"],
                        data=data,
                    )
                except Exception as exception:
                    _LOGGER.error(exception)
                    errors = {"base": "invalid_code"}

        return self.async_show_form(
            step_id="challenge",
            data_schema=CHALLENGE_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Handle reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._pending_user_input = {
            "username": entry_data["username"],
            "password": entry_data["password"],
            "includeTransactions": entry_data["includeTransactions"],
        }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask for credentials again when the token has expired."""
        if user_input is not None:
            data = dict(self._pending_user_input)
            data.update(user_input)
            result = await self._authenticate(data)
            if isinstance(result, dict) and result.get("token"):
                data["token"] = result["token"]
                data["cookies"] = result.get("cookies", {})
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data=data,
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            if isinstance(result, MyEdenredChallengeRequired):
                self._pending_user_input = data
                self._pending_challenge = result.challenge
                return await self.async_step_challenge()
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=DATA_SCHEMA,
                errors={"base": "auth"},
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=DATA_SCHEMA,
        )

    async def _authenticate(self, user_input):
        """Return authentication data or a challenge-required marker."""
        session = async_get_clientsession(self.hass, True)
        async with async_timeout.timeout(10):
            api = MY_EDENRED(session)
            try:
                return await api.authenticate(
                    user_input["username"], user_input["password"]
                )
            except MyEdenredChallengeRequired as exception:
                return exception
            except MyEdenredAuthError as exception:
                _LOGGER.error(exception)
                return None
            except Exception as exception:
                _LOGGER.error(exception)
                return None
