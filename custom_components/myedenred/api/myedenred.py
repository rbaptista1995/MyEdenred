"""API to MYEDENRED."""
import aiohttp
import base64
import json as jsonlib
import logging
from datetime import datetime, timezone

from .account import Account
from .card import Card
from .consts import (
    API_COMMON_PARAMS,
    API_LOGIN_CHALLENGE_URL,
    API_LOGIN_URL,
    API_LIST_URL,
    API_ACCOUNTMOVEMENT_URL
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


class MyEdenredError(Exception):
    """Base exception for MyEdenred API errors."""


class MyEdenredAuthError(MyEdenredError):
    """Raised when authentication fails."""


class MyEdenredChallengeRequired(MyEdenredAuthError):
    """Raised when MyEdenred requires an email 2FA code."""

    def __init__(self, challenge):
        super().__init__("MyEdenred requires a 2FA challenge code")
        self.challenge = challenge


def _challenge_id_from(data):
    """Return the 2FA challenge id from an API payload, if any."""
    if not isinstance(data, dict):
        return None
    return data.get("authenticationMfaProcessId") or data.get("challengeId")


def _log_token_expiry(token):
    """Log the JWT expiration time (best effort) to ease diagnostics."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = jsonlib.loads(base64.urlsafe_b64decode(payload))
        exp = claims.get("exp")
        if exp:
            _LOGGER.debug(
                "MyEdenred token expires at %s",
                datetime.fromtimestamp(exp, tz=timezone.utc),
            )
    except (IndexError, ValueError) as err:
        _LOGGER.debug("Unable to decode MyEdenred token expiry: %s", err)


class MY_EDENRED:
    """Interfaces to https://myedenred.pt/"""

    def __init__(self, websession, cookies=None):
        self.websession = websession
        self.json = None
        self.cookies = cookies or {}

    def _cookie_header(self):
        """Return stored cookies as a HTTP Cookie header."""
        if not self.cookies:
            return None
        return "; ".join(
            f"{name}={value}" for name, value in self.cookies.items() if value
        )

    def _headers(self, token=None):
        """Return common request headers."""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token
        cookie_header = self._cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header
        return headers

    async def _request_json(self, method, url, **kwargs):
        """Issue a request and return the JSON body."""
        async with self.websession.request(method, url, **kwargs) as res:
            if res.cookies:
                self.cookies.update(
                    {
                        name: morsel.value
                        for name, morsel in res.cookies.items()
                    }
                )
            if res.content_type != "application/json":
                raise MyEdenredError("Unexpected response from MyEdenred API")
            json = await res.json()
            if res.status == 200:
                return json
            if res.status == 401:
                # The API may signal a required 2FA challenge in the 401 body.
                if _challenge_id_from(json.get("data") if isinstance(json, dict) else None):
                    raise MyEdenredChallengeRequired(json.get("data"))
                raise MyEdenredAuthError("MyEdenred authentication failed")
            message = json.get("message", "MyEdenred API request failed") if isinstance(json, dict) else "MyEdenred API request failed"
            raise MyEdenredError(message)

    async def authenticate(self, username, password):
        """Issue LOGIN request."""
        try:
            _LOGGER.debug("Logging in...")
            json = await self._request_json(
                "POST",
                API_LOGIN_URL,
                params=API_COMMON_PARAMS,
                headers=self._headers(),
                json={"userId": username, "password": password},
            )
            data = json.get("data", {})
            data["cookies"] = self.cookies
            if _challenge_id_from(data):
                raise MyEdenredChallengeRequired(data)
            if data.get("token"):
                _LOGGER.debug("Done logging in.")
                _log_token_expiry(data["token"])
                return data
            raise MyEdenredAuthError("Could not retrieve token for user, login failed")
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err

    async def login(self, username, password):
        """Issue LOGIN request and return a token."""
        data = await self.authenticate(username, password)
        return data.get("token")

    async def login_with_challenge(self, username, password, challenge, code):
        """Issue LOGIN request with an email 2FA challenge code."""
        try:
            challenge_id = challenge.get("authenticationMfaProcessId")
            if not challenge_id:
                challenge_id = challenge.get("challengeId")

            json = await self._request_json(
                "POST",
                API_LOGIN_CHALLENGE_URL,
                params=API_COMMON_PARAMS,
                headers=self._headers(),
                json={
                    "userId": username,
                    "password": password,
                    "authenticationMfaProcessId": challenge_id,
                    "token": code,
                },
            )
            data = json.get("data", {})
            data["cookies"] = self.cookies
            if data.get("token"):
                _log_token_expiry(data["token"])
                return data
            raise MyEdenredAuthError("Could not retrieve token after 2FA challenge")
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err

    async def getCards(self, token) -> Card:
        """Issue CARDS requests."""
        try:
            _LOGGER.debug("Getting list of available cards...")
            json = await self._request_json(
                "GET",
                API_LIST_URL,
                params=API_COMMON_PARAMS,
                headers=self._headers(token),
            )
            _LOGGER.debug("Done getting list of available cards.")
            return [Card(card) for card in json["data"]]
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err

    async def getAccountDetails(self, cardId, token) -> Account:
        """Issue ACCOUNT MOVEMENT requests."""
        try:
            _LOGGER.debug("Getting card details and their movements...")
            json = await self._request_json(
                "GET",
                API_ACCOUNTMOVEMENT_URL.format(cardId),
                params=API_COMMON_PARAMS,
                headers=self._headers(token),
            )
            _LOGGER.debug("Done getting card details and their movements.")
            return Account(json["data"]["account"], json["data"]["movementList"])
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err
