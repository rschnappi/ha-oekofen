"""Tests for the ÖkOfen Pellematic API client (session handling, auth, data I/O)."""
import asyncio

import pytest
from aioresponses import aioresponses
from multidict import CIMultiDict

from custom_components.oekofen.pellematic_api import PellematicAPI

BASE_URL = "http://device.local"
INDEX_URL = f"{BASE_URL}/index.cgi"
GET_URL = f"{BASE_URL}/?action=get&attr=1"
SET_URL = f"{BASE_URL}/?action=set"


def login_headers(pksession="abc123", login_error=None):
    """Build Set-Cookie response headers like the real device sends on login."""
    headers = CIMultiDict()
    if pksession is not None:
        headers.add("Set-Cookie", f"pksession={pksession}; Path=/")
    if login_error is not None:
        headers.add("Set-Cookie", f"LoginError={login_error}; Path=/")
    return headers


def data_payload(params, value="1"):
    return [
        {
            "name": p,
            "value": value,
            "status": "OK",
            "divisor": "",
            "formatTexts": "",
            "shortText": "",
            "unitText": "",
            "lowerLimit": "",
            "upperLimit": "",
        }
        for p in params
    ]


@pytest.fixture
async def api():
    client = PellematicAPI(BASE_URL, "user", "pass")
    yield client
    await client.close()


class TestAuthenticate:
    async def test_success_sets_authenticated(self, api):
        with aioresponses() as m:
            m.post(INDEX_URL, status=303, headers=login_headers())
            result = await api.authenticate()
        assert result is True
        assert api._authenticated is True

    async def test_invalid_credentials_returns_false(self, api):
        with aioresponses() as m:
            m.post(INDEX_URL, status=303, headers=login_headers(pksession=None, login_error="1"))
            result = await api.authenticate()
        assert result is False
        assert api._authenticated is False

    async def test_missing_session_cookie_returns_false(self, api):
        with aioresponses() as m:
            m.post(INDEX_URL, status=200, headers=CIMultiDict())
            result = await api.authenticate()
        assert result is False

    async def test_concurrent_calls_only_trigger_one_login(self, api):
        """Regression test: the asyncio.Lock must prevent duplicate logins
        when two callers (e.g. the poll coordinator and a service call) hit
        an expired session at the same time."""
        with aioresponses() as m:
            m.post(INDEX_URL, status=303, headers=login_headers(), repeat=True)
            results = await asyncio.gather(api.authenticate(), api.authenticate())

        assert results == [True, True]
        login_calls = [
            calls for (method, url), calls in m.requests.items()
            if method == "POST" and url.path == "/index.cgi"
        ]
        total_calls = sum(len(calls) for calls in login_calls)
        assert total_calls == 1

    async def test_already_authenticated_skips_network_call(self, api):
        api._authenticated = True
        with aioresponses() as m:
            # No handler registered - a real request would raise ConnectionError
            result = await api.authenticate()
        assert result is True


class TestGetData:
    async def test_success_parses_response(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(GET_URL, status=200, payload=data_payload(["CAPPL:X"], value="42"))
            data = await api.get_data(["CAPPL:X"])
        assert data["CAPPL:X"]["value"] == "42"
        assert data["CAPPL:X"]["status"] == "OK"

    async def test_html_response_triggers_reauth_and_retry(self, api):
        """The device answers HTTP 200 with the login page (HTML) instead of
        JSON once the session has expired - this must be treated like a 401."""
        api._authenticated = True
        with aioresponses() as m:
            m.post(GET_URL, status=200, body="<html>login</html>", content_type="text/html")
            m.post(INDEX_URL, status=303, headers=login_headers())
            m.post(GET_URL, status=200, payload=data_payload(["CAPPL:X"]))
            data = await api.get_data(["CAPPL:X"])
        assert data["CAPPL:X"]["value"] == "1"

    async def test_401_triggers_reauth_and_retry(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(GET_URL, status=401)
            m.post(INDEX_URL, status=303, headers=login_headers())
            m.post(GET_URL, status=200, payload=data_payload(["CAPPL:X"]))
            data = await api.get_data(["CAPPL:X"])
        assert data["CAPPL:X"]["value"] == "1"

    async def test_reauth_failure_raises(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(GET_URL, status=401)
            m.post(INDEX_URL, status=200, headers=CIMultiDict())  # login fails, no cookie
            with pytest.raises(Exception, match="Re-authentication failed"):
                await api.get_data(["CAPPL:X"])

    async def test_initial_auth_failure_raises(self, api):
        with aioresponses() as m:
            m.post(INDEX_URL, status=200, headers=CIMultiDict())
            with pytest.raises(Exception, match="Authentication failed"):
                await api.get_data(["CAPPL:X"])

    async def test_unexpected_status_raises(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(GET_URL, status=500)
            with pytest.raises(Exception, match="HTTP 500"):
                await api.get_data(["CAPPL:X"])


class TestSetData:
    async def test_applies_divisor_and_returns_display_value(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(SET_URL, status=200, payload=[{"status": "OK", "value": "200"}])
            result = await api.set_data("CAPPL:LOCAL.hk[0].raumtemp_heizen", 20.0, divisor=10)

        assert result["status"] == "OK"
        assert result["raw_value"] == "200"
        assert result["display_value"] == 20.0

        (_, sent_kwargs), = [
            (call.args, call.kwargs)
            for calls in m.requests.values()
            for call in calls
        ][-1:]
        assert sent_kwargs["json"] == {"CAPPL:LOCAL.hk[0].raumtemp_heizen": 200}

    async def test_html_response_triggers_reauth_and_retry(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(SET_URL, status=200, body="<html>login</html>")
            m.post(INDEX_URL, status=303, headers=login_headers())
            m.post(SET_URL, status=200, payload=[{"status": "OK", "value": "200"}])
            result = await api.set_data("CAPPL:X", 20.0, divisor=10)
        assert result["status"] == "OK"

    async def test_failed_status_raises(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(SET_URL, status=200, payload=[{"status": "ERROR"}])
            with pytest.raises(Exception, match="Set failed"):
                await api.set_data("CAPPL:X", 20.0)

    async def test_no_divisor_sends_raw_value(self, api):
        api._authenticated = True
        with aioresponses() as m:
            m.post(SET_URL, status=200, payload=[{"status": "OK", "value": "1"}])
            result = await api.set_data("CAPPL:LOCAL.anlage_betriebsart", 1)

        assert result["display_value"] == "1"
        (_, sent_kwargs), = [
            (call.args, call.kwargs)
            for calls in m.requests.values()
            for call in calls
        ][-1:]
        assert sent_kwargs["json"] == {"CAPPL:LOCAL.anlage_betriebsart": 1}
