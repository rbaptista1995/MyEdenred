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
    API_LOGIN_CHALLENGE_RESEND_URL,
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


def _data_payload(json_body):
    """Return the dict data payload from an API body, if any."""
    if isinstance(json_body, dict) and isinstance(json_body.get("data"), dict):
        return json_body["data"]
    return {}


TOKEN_FIELD_NAMES = ("token", "refreshToken", "sessionToken")


def _jwt_claims(token):
    """Return the decoded JWT claims without exposing the raw token."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return jsonlib.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, TypeError) as err:
        _LOGGER.debug("Unable to decode MyEdenred token claims: %s", err)
        return None


def _log_token_expiry(token):
    """Log JWT iat/exp/lifetime/remaining (best effort), never the token."""
    claims = _jwt_claims(token)
    if not claims:
        return
    iat = claims.get("iat")
    exp = claims.get("exp")
    if not exp:
        return
    now = datetime.now(timezone.utc).timestamp()
    details = ["MyEdenred token expires at %s"]
    args = [datetime.fromtimestamp(exp, tz=timezone.utc)]
    if iat:
        details.append(
            "iat=%s exp=%s lifetime=%ss remaining=%ss"
        )
        args.extend(
            [
                datetime.fromtimestamp(iat, tz=timezone.utc),
                datetime.fromtimestamp(exp, tz=timezone.utc),
                int(exp - iat),
                int(exp - now),
            ]
        )
    _LOGGER.debug(" ".join(details), *args)


def _log_token_timing(token, context):
    """Log token age and seconds remaining, never the token itself."""
    claims = _jwt_claims(token) if token else None
    if not claims or not claims.get("exp"):
        return
    now = datetime.now(timezone.utc).timestamp()
    issued = claims.get("iat", claims["exp"])
    _LOGGER.debug(
        "MyEdenred %s: token age=%ss remaining=%ss",
        context,
        int(now - issued),
        int(claims["exp"] - now),
    )


def _token_like_fields(*payloads):
    """Return token-like keys present in payloads, keys only, no values."""
    found = []
    for payload in payloads:
        if isinstance(payload, dict):
            found.extend(name for name in TOKEN_FIELD_NAMES if name in payload)
    return sorted(set(found))


def _log_response_diagnostics(res, json_body=None, had_authorization=False):
    """Log response shape only: status, content type, header/field presence."""
    _LOGGER.debug(
        "MyEdenred response: status=%s content_type=%s set_cookie=%s"
        " authorization_sent=%s token_fields=%s",
        res.status,
        res.content_type,
        bool(res.cookies),
        had_authorization,
        _token_like_fields(json_body, _data_payload(json_body)) if json_body is not None else [],
    )


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

    async def _request_json(self, method, url, token=None, **kwargs):
        """Issue a request and return the JSON body."""
        async with self.websession.request(method, url, **kwargs) as res:
            set_cookie = bool(res.cookies)
            if res.cookies:
                self.cookies.update(
                    {
                        name: morsel.value
                        for name, morsel in res.cookies.items()
                    }
                )
            if res.content_type != "application/json":
                _log_response_diagnostics(res, had_authorization=bool(token))
                raise MyEdenredError("Unexpected response from MyEdenred API")
            try:
                json = await res.json()
            except (jsonlib.JSONDecodeError, UnicodeDecodeError) as err:
                _log_response_diagnostics(res, had_authorization=bool(token))
                raise MyEdenredError("Invalid JSON response from MyEdenred API") from err
            _log_response_diagnostics(
                res, json_body=json, had_authorization=bool(token)
            )
            if res.status == 200:
                return json
            if res.status == 401:
                _log_token_timing(token, "401 received")
                _LOGGER.debug("MyEdenred 401: set_cookie=%s", set_cookie)
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
            data = _data_payload(json)
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
            data = _data_payload(json)
            data["cookies"] = self.cookies
            if data.get("token"):
                _log_token_expiry(data["token"])
                return data
            raise MyEdenredAuthError("Could not retrieve token after 2FA challenge")
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err

    async def resend_challenge(self, challenge):
        """Ask MyEdenred to email a fresh 2FA code for the active challenge."""
        try:
            challenge_id = challenge.get("authenticationMfaProcessId")
            if not challenge_id:
                challenge_id = challenge.get("challengeId")

            _LOGGER.debug("Requesting a new 2FA code...")
            json = await self._request_json(
                "POST",
                API_LOGIN_CHALLENGE_RESEND_URL,
                params=API_COMMON_PARAMS,
                headers=self._headers(),
                json={"authenticationMfaProcessId": challenge_id},
            )
            data = _data_payload(json)
            data["cookies"] = self.cookies
            if _challenge_id_from(data):
                _LOGGER.debug("Done requesting a new 2FA code.")
                raise MyEdenredChallengeRequired(data)
            raise MyEdenredError("MyEdenred did not return a new 2FA challenge")
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err

    async def getCards(self, token) -> Card:
        """Issue CARDS requests."""
        try:
            _LOGGER.debug("Getting list of available cards...")
            _log_token_timing(token, "getCards")
            json = await self._request_json(
                "GET",
                API_LIST_URL,
                token=token,
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
            _log_token_timing(token, "getAccountDetails")
            json = await self._request_json(
                "GET",
                API_ACCOUNTMOVEMENT_URL.format(cardId),
                token=token,
                params=API_COMMON_PARAMS,
                headers=self._headers(token),
            )
            _LOGGER.debug("Done getting card details and their movements.")
            return Account(json["data"]["account"], json["data"]["movementList"])
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise MyEdenredError(err) from err
