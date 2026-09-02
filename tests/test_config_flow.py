"""Tests for MyEdenred config flow error handling."""
import asyncio

import aiohttp

from custom_components.myedenred import config_flow

LOGIN_OK = (200, {"data": {"token": "tok", "cookies": {}}})
CHALLENGE = (200, {"data": {"authenticationMfaProcessId": "challenge-1"}})


class FakeCookie:
    def __init__(self, value):
        self.value = value


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body
        self.content_type = "application/json"
        self.cookies = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def json(self):
        return self.body


class _PendingResponse:
    def __init__(self, awaitable):
        self.awaitable = awaitable

    async def __aenter__(self):
        return await self.awaitable

    async def __aexit__(self, *exc_info):
        return False


class FakeSession:
    def __init__(self, handler):
        self.handler = handler

    def request(self, method, url, **kwargs):
        result = self.handler(method, url, kwargs)
        if asyncio.iscoroutine(result):
            return _PendingResponse(result)
        return result


class FakeHass:
    def __init__(self, session):
        self.session = session


class FakeConfigEntries:
    def __init__(self, entry):
        self._entry = entry

    def async_get_entry(self, entry_id):
        return self._entry


class FakeEntry:
    def __init__(self, data):
        self.entry_id = "entry-1"
        self.data = data


def make_flow(handler):
    flow = config_flow.ConfigFlow()
    flow.hass = FakeHass(FakeSession(handler))
    return flow


def make_reauth_flow(handler, data=None):
    flow = make_flow(handler)
    entry = FakeEntry(
        data
        or {
            "username": "user@example.com",
            "password": "old",
            "includeTransactions": False,
        }
    )
    flow.hass.config_entries = FakeConfigEntries(entry)
    flow.context = {"entry_id": entry.entry_id}
    return flow, entry


def user_input():
    return {"username": "user@example.com", "password": "secret", "includeTransactions": False}


def test_timeout_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(config_flow, "AUTH_TIMEOUT_SECONDS", 0.2)

    async def slow(method, url, kwargs):
        await asyncio.sleep(5)
        return FakeResponse(*LOGIN_OK)

    result = asyncio.run(make_flow(slow).async_step_user(user_input()))
    assert result["errors"] == {"base": "timeout"}


def test_timeout_raised_by_session_is_reported():
    def handler(method, url, kwargs):
        raise asyncio.TimeoutError()

    result = asyncio.run(make_flow(handler).async_step_user(user_input()))
    assert result["errors"] == {"base": "timeout"}


def test_network_error_is_reported_not_raised():
    def handler(method, url, kwargs):
        raise aiohttp.ClientConnectionError("connection reset")

    result = asyncio.run(make_flow(handler).async_step_user(user_input()))
    assert result["errors"] == {"base": "network"}


def test_invalid_credentials_show_auth_error():
    def handler(method, url, kwargs):
        return FakeResponse(401, {"message": "Invalid credentials", "data": {}})

    result = asyncio.run(make_flow(handler).async_step_user(user_input()))
    assert result["errors"] == {"base": "auth"}


def test_challenge_required_shows_challenge_form():
    result = asyncio.run(make_flow(lambda *args: FakeResponse(*CHALLENGE)).async_step_user(user_input()))
    assert result["step_id"] == "challenge"
    assert result["errors"] == {}


def test_invalid_challenge_code_shows_invalid_code():
    calls = []

    def handler(method, url, kwargs):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(*CHALLENGE)
        return FakeResponse(401, {"message": "wrong code", "data": {}})

    flow = make_flow(handler)
    asyncio.run(flow.async_step_user(user_input()))
    result = asyncio.run(flow.async_step_challenge({"code": "000000"}))
    assert result["step_id"] == "challenge"
    assert result["errors"] == {"base": "invalid_code"}


def test_resend_code_requests_a_new_challenge():
    calls = []

    def handler(method, url, kwargs):
        calls.append(url)
        if "resend" in url:
            return FakeResponse(
                200, {"data": {"authenticationMfaProcessId": "challenge-2"}}
            )
        return FakeResponse(*CHALLENGE)

    flow = make_flow(handler)
    asyncio.run(flow.async_step_user(user_input()))
    result = asyncio.run(
        flow.async_step_challenge({"code": "", "resend_code": True})
    )
    assert result["step_id"] == "challenge"
    assert result["errors"] == {}
    assert flow._pending_challenge["authenticationMfaProcessId"] == "challenge-2"
    assert any("resend" in url for url in calls)


def test_reauth_with_rejected_password_asks_for_a_new_one():
    def handler(method, url, kwargs):
        if kwargs.get("json", {}).get("password") == "old":
            return FakeResponse(401, {"message": "Invalid credentials", "data": {}})
        return FakeResponse(*CHALLENGE)

    flow, _ = make_reauth_flow(handler)
    result = asyncio.run(
        flow.async_step_reauth(
            {
                "username": "user@example.com",
                "password": "old",
                "includeTransactions": False,
            }
        )
    )
    assert result["step_id"] == "reauth_credentials"

    result = asyncio.run(flow.async_step_reauth_credentials({"password": "new"}))
    assert result["step_id"] == "challenge"
