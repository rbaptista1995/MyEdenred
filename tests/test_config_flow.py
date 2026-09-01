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


def make_flow(handler):
    flow = config_flow.ConfigFlow()
    flow.hass = FakeHass(FakeSession(handler))
    return flow


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
