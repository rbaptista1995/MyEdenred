"""Config flow for myEdenred integration."""
from __future__ import annotations

import asyncio
import logging

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.myedenred import (
    MY_EDENRED,
    MyEdenredAuthError,
    MyEdenredChallengeRequired,
    MyEdenredError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

AUTH_TIMEOUT_SECONDS = 30

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Required("includeTransactions"): bool,
    }
)

CHALLENGE_SCHEMA = vol.Schema(
    {
        vol.Required("code"): str,
        vol.Optional("resend_code", default=False): bool,
    }
)
REAUTH_SCHEMA = vol.Schema({})
REAUTH_CREDENTIALS_SCHEMA = vol.Schema({vol.Required("password"): str})


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
                    data=user_input,
                )
            if isinstance(result, MyEdenredChallengeRequired):
                self._pending_user_input = user_input
                self._pending_challenge = result.challenge
                return await self.async_step_challenge()
            errors = {"base": result if isinstance(result, str) else "auth"}

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
            api = MY_EDENRED(session, self._pending_challenge.get("cookies"))

            if user_input.get("resend_code"):
                try:
                    async with async_timeout.timeout(AUTH_TIMEOUT_SECONDS):
                        await api.resend_challenge(self._pending_challenge)
                except MyEdenredChallengeRequired as err:
                    # A fresh challenge carries the new code sent by email.
                    self._pending_challenge = err.challenge
                except MyEdenredAuthError as err:
                    _LOGGER.error("MyEdenred could not resend the 2FA code: %s", err)
                    errors = {"base": "resend_failed"}
                except asyncio.TimeoutError:
                    _LOGGER.error("MyEdenred 2FA resend timed out")
                    errors = {"base": "timeout"}
                except (aiohttp.ClientError, MyEdenredError) as err:
                    _LOGGER.error("MyEdenred 2FA resend failed: %s", err)
                    errors = {"base": "network"}
                return self.async_show_form(
                    step_id="challenge",
                    data_schema=CHALLENGE_SCHEMA,
                    errors=errors,
                )

            result = None
            try:
                async with async_timeout.timeout(AUTH_TIMEOUT_SECONDS):
                    result = await api.login_with_challenge(
                        self._pending_user_input["username"],
                        self._pending_user_input["password"],
                        self._pending_challenge,
                        user_input["code"],
                    )
            except MyEdenredChallengeRequired:
                # A rejected code makes the API issue a fresh challenge.
                _LOGGER.error("MyEdenred rejected the 2FA code and issued a new challenge")
                errors = {"base": "invalid_code"}
            except MyEdenredAuthError as err:
                _LOGGER.error("MyEdenred rejected the 2FA code: %s", err)
                errors = {"base": "invalid_code"}
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "MyEdenred 2FA request timed out after %s seconds",
                    AUTH_TIMEOUT_SECONDS,
                )
                errors = {"base": "timeout"}
            except (aiohttp.ClientError, MyEdenredError) as err:
                _LOGGER.error("MyEdenred 2FA request failed: %s", err)
                errors = {"base": "network"}

            if result is not None:
                data = (
                    {**self._reauth_entry.data, **self._pending_user_input}
                    if self._reauth_entry
                    else dict(self._pending_user_input)
                )
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

        return self.async_show_form(
            step_id="challenge",
            data_schema=CHALLENGE_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Handle reauthentication triggered by an expired token."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._pending_user_input = {
            "username": entry_data["username"],
            "password": entry_data["password"],
            "includeTransactions": entry_data["includeTransactions"],
        }

        return await self._start_reauth(entry_data)

    async def async_step_reauth_confirm(self, user_input=None):
        """Retry starting 2FA without asking for saved credentials."""
        if user_input is not None:
            return await self._start_reauth(self._reauth_entry.data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
        )

    async def async_step_reauth_credentials(self, user_input=None):
        """Collect a new password when the stored one is rejected."""
        errors = {}

        if user_input is not None:
            self._pending_user_input["password"] = user_input["password"]
            result = await self._authenticate(
                self._pending_user_input,
                cookies=self._reauth_entry.data.get("cookies"),
            )
            if isinstance(result, dict) and result.get("token"):
                data = {
                    **self._reauth_entry.data,
                    **self._pending_user_input,
                    "token": result["token"],
                    "cookies": result.get("cookies", {}),
                }
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, data=data
                )
                await self.hass.config_entries.async_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")
            if isinstance(result, MyEdenredChallengeRequired):
                self._pending_challenge = result.challenge
                return await self.async_step_challenge()
            errors = {"base": result if result == "auth" else "reauth_failed"}

        return self.async_show_form(
            step_id="reauth_credentials",
            data_schema=REAUTH_CREDENTIALS_SCHEMA,
            errors=errors,
        )

    async def _start_reauth(self, entry_data):
        """Use saved credentials once and continue directly to the 2FA code."""
        result = await self._authenticate(
            self._pending_user_input,
            cookies=entry_data.get("cookies"),
        )
        if isinstance(result, dict) and result.get("token"):
            data = {
                **entry_data,
                "token": result["token"],
                "cookies": result.get("cookies", {}),
            }
            self.hass.config_entries.async_update_entry(self._reauth_entry, data=data)
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        if isinstance(result, MyEdenredChallengeRequired):
            self._pending_challenge = result.challenge
            return await self.async_step_challenge()
        if result == "auth":
            # The stored password is stale: ask for a new one instead of
            # looping forever on reauth_confirm.
            return await self.async_step_reauth_credentials()
        error = result if result in ("timeout", "network") else "reauth_failed"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors={"base": error},
        )

    async def _authenticate(self, user_input, cookies=None):
        """Return authentication data, a challenge marker, or an error key."""
        session = async_get_clientsession(self.hass, True)
        api = MY_EDENRED(session, cookies)
        try:
            async with async_timeout.timeout(AUTH_TIMEOUT_SECONDS):
                return await api.authenticate(
                    user_input["username"], user_input["password"]
                )
        except MyEdenredChallengeRequired as err:
            _LOGGER.debug("MyEdenred requires an email 2FA challenge")
            return err
        except MyEdenredAuthError as err:
            _LOGGER.error("MyEdenred rejected the credentials: %s", err)
            return "auth"
        except asyncio.TimeoutError:
            _LOGGER.error(
                "MyEdenred authentication timed out after %s seconds",
                AUTH_TIMEOUT_SECONDS,
            )
            return "timeout"
        except (aiohttp.ClientError, MyEdenredError) as err:
            _LOGGER.error("MyEdenred authentication request failed: %s", err)
            return "network"
