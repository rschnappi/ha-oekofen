"""Tests for the ÖkOfen Pellematic API client (session handling, auth, data I/O).

Uses a real local aiohttp.web server (via aiohttp.test_utils.TestServer)
instead of aioresponses: aioresponses patches aiohttp's ClientResponse
internals directly, which breaks on every aiohttp release that changes that
constructor's signature - confirmed broken as of aiohttp 3.10+
(TypeError: ClientResponse.__init__() missing 'stream_writer'), forcing an
artificial aiohttp<3.10 pin that in turn blocks testing against any
currently-unaffected/patched homeassistant release. Driving PellematicAPI's
real aiohttp.ClientSession against a real (local) server only touches
aiohttp's public web/client APIs, so it keeps working across aiohttp
versions.
"""
import asyncio
import importlib.util
import json
import pathlib

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

# Load pellematic_api.py directly by file path instead of via the
# custom_components.oekofen package. pellematic_api.py itself has no
# Home Assistant dependency, but importing it as a package submodule would
# execute custom_components/oekofen/__init__.py first (Python always runs a
# parent package's __init__.py on submodule import), which pulls in
# voluptuous/homeassistant - dependencies these tests intentionally avoid.
_MODULE_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components" / "oekofen" / "pellematic_api.py"
)
_spec = importlib.util.spec_from_file_location("pellematic_api", _MODULE_PATH)
_pellematic_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pellematic_api)
PellematicAPI = _pellematic_api.PellematicAPI


def login_headers(pksession="abc123", login_error=None):
    """Set-Cookie header pairs like the real device sends on login."""
    headers = []
    if pksession is not None:
        headers.append(("Set-Cookie", f"pksession={pksession}; Path=/"))
    if login_error is not None:
        headers.append(("Set-Cookie", f"LoginError={login_error}; Path=/"))
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


class FakeDevice:
    """A real local aiohttp.web server standing in for the ÖkOfen device.

    Each endpoint is driven by a queue of response specs: register one dict
    per expected call (in order) via queue_index/queue_get/queue_set. A spec
    is {"status":, "headers": [...], "body": str, "payload": obj}. Every
    handled request is recorded (path, query, headers, parsed body) in
    `.requests` for assertions.
    """

    def __init__(self):
        self._index_queue = []
        self._get_queue = []
        self._set_queue = []
        self.requests = []
        self._server = None
        self.url = None

    async def start(self):
        app = web.Application()
        app.router.add_post("/index.cgi", self._handle_index)
        app.router.add_post("/", self._handle_root)
        self._server = TestServer(app)
        await self._server.start_server()
        self.url = str(self._server.make_url("")).rstrip("/")

    async def stop(self):
        if self._server is not None:
            await self._server.close()

    def queue_index(self, **spec):
        self._index_queue.append(spec)

    def queue_get(self, **spec):
        self._get_queue.append(spec)

    def queue_set(self, **spec):
        self._set_queue.append(spec)

    async def _handle_index(self, request):
        body = await request.post()
        self.requests.append({"path": request.path, "query": dict(request.query), "body": dict(body)})
        spec = self._index_queue.pop(0) if self._index_queue else {"status": 200}
        return self._build_response(spec)

    async def _handle_root(self, request):
        raw = await request.text()
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw
        self.requests.append({"path": request.path, "query": dict(request.query), "json": body})
        queue = self._get_queue if request.query.get("action") == "get" else self._set_queue
        spec = queue.pop(0) if queue else {"status": 200}
        return self._build_response(spec)

    @staticmethod
    def _build_response(spec):
        status = spec.get("status", 200)
        if "payload" in spec:
            resp = web.json_response(spec["payload"], status=status)
        else:
            body = spec.get("body")
            if isinstance(body, str):
                resp = web.Response(status=status, text=body, content_type=spec.get("content_type"))
            else:
                resp = web.Response(status=status, body=body, content_type=spec.get("content_type"))
        for name, value in spec.get("headers", []):
            resp.headers.add(name, value)
        return resp


@pytest.fixture
async def device():
    fake = FakeDevice()
    await fake.start()
    yield fake
    await fake.stop()


@pytest.fixture
async def api(device):
    client = PellematicAPI(device.url, "user", "pass")
    yield client
    await client.close()


class TestAuthenticate:
    async def test_success_sets_authenticated(self, api, device):
        device.queue_index(status=303, headers=login_headers())
        result = await api.authenticate()
        assert result is True
        assert api._authenticated is True

    async def test_invalid_credentials_returns_false(self, api, device):
        device.queue_index(status=303, headers=login_headers(pksession=None, login_error="1"))
        result = await api.authenticate()
        assert result is False
        assert api._authenticated is False

    async def test_missing_session_cookie_returns_false(self, api, device):
        device.queue_index(status=200)
        result = await api.authenticate()
        assert result is False

    async def test_concurrent_calls_only_trigger_one_login(self, api, device):
        """Regression test: the asyncio.Lock must prevent duplicate logins
        when two callers (e.g. the poll coordinator and a service call) hit
        an expired session at the same time."""
        device.queue_index(status=303, headers=login_headers())
        device.queue_index(status=303, headers=login_headers())
        results = await asyncio.gather(api.authenticate(), api.authenticate())

        assert results == [True, True]
        login_calls = [r for r in device.requests if r["path"] == "/index.cgi"]
        assert len(login_calls) == 1

    async def test_already_authenticated_skips_network_call(self, api, device):
        api._authenticated = True
        # No handler queued - authenticate() must return early without
        # making a request, otherwise the fake server would answer with the
        # default 200/no-cookie response and this would fail below.
        result = await api.authenticate()
        assert result is True
        assert device.requests == []


class TestGetData:
    async def test_success_parses_response(self, api, device):
        api._authenticated = True
        device.queue_get(status=200, payload=data_payload(["CAPPL:X"], value="42"))
        data = await api.get_data(["CAPPL:X"])
        assert data["CAPPL:X"]["value"] == "42"
        assert data["CAPPL:X"]["status"] == "OK"

    async def test_html_response_triggers_reauth_and_retry(self, api, device):
        """The device answers HTTP 200 with the login page (HTML) instead of
        JSON once the session has expired - this must be treated like a 401."""
        api._authenticated = True
        device.queue_get(status=200, body="<html>login</html>", content_type="text/html")
        device.queue_index(status=303, headers=login_headers())
        device.queue_get(status=200, payload=data_payload(["CAPPL:X"]))
        data = await api.get_data(["CAPPL:X"])
        assert data["CAPPL:X"]["value"] == "1"

    async def test_401_triggers_reauth_and_retry(self, api, device):
        api._authenticated = True
        device.queue_get(status=401)
        device.queue_index(status=303, headers=login_headers())
        device.queue_get(status=200, payload=data_payload(["CAPPL:X"]))
        data = await api.get_data(["CAPPL:X"])
        assert data["CAPPL:X"]["value"] == "1"

    async def test_reauth_failure_raises(self, api, device):
        api._authenticated = True
        device.queue_get(status=401)
        device.queue_index(status=200)  # login fails, no cookie
        with pytest.raises(Exception, match="Re-authentication failed"):
            await api.get_data(["CAPPL:X"])

    async def test_initial_auth_failure_raises(self, api, device):
        device.queue_index(status=200)
        with pytest.raises(Exception, match="Authentication failed"):
            await api.get_data(["CAPPL:X"])

    async def test_unexpected_status_raises(self, api, device):
        api._authenticated = True
        device.queue_get(status=500)
        with pytest.raises(Exception, match="HTTP 500"):
            await api.get_data(["CAPPL:X"])


class TestSetData:
    async def test_applies_divisor_and_returns_display_value(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, payload=[{"status": "OK", "value": "200"}])
        result = await api.set_data("CAPPL:LOCAL.hk[0].raumtemp_heizen", 20.0, divisor=10)

        assert result["status"] == "OK"
        assert result["raw_value"] == "200"
        assert result["display_value"] == 20.0

        sent = [r for r in device.requests if r["path"] == "/"][-1]
        assert sent["json"] == {"CAPPL:LOCAL.hk[0].raumtemp_heizen": 200}

    async def test_html_response_triggers_reauth_and_retry(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, body="<html>login</html>")
        device.queue_index(status=303, headers=login_headers())
        device.queue_set(status=200, payload=[{"status": "OK", "value": "200"}])
        result = await api.set_data("CAPPL:X", 20.0, divisor=10)
        assert result["status"] == "OK"

    async def test_failed_status_raises(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, payload=[{"status": "ERROR"}])
        with pytest.raises(Exception, match="Set failed"):
            await api.set_data("CAPPL:X", 20.0)

    async def test_no_divisor_sends_raw_value(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, payload=[{"status": "OK", "value": "1"}])
        result = await api.set_data("CAPPL:LOCAL.anlage_betriebsart", 1)

        assert result["display_value"] == "1"
        sent = [r for r in device.requests if r["path"] == "/"][-1]
        assert sent["json"] == {"CAPPL:LOCAL.anlage_betriebsart": 1}


class TestSetDataMulti:
    async def test_sends_all_parameters_in_one_request_and_maps_by_name(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, payload=[
            {"name": "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu", "status": "OK", "value": "1700000000"},
            {"name": "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit", "status": "OK", "value": "1"},
        ])
        result = await api.set_data_multi({
            "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu": 1700000000,
            "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit": 1,
        })

        assert result == {
            "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu": "1700000000",
            "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit": "1",
        }
        sent = [r for r in device.requests if r["path"] == "/"][-1]
        assert sent["json"] == {
            "CAPPL:LOCAL.L_fernwartung_uhrzeit_neu": 1700000000,
            "CAPPL:LOCAL.L_fernwartung_setze_uhrzeit": 1,
        }

    async def test_html_response_triggers_reauth_and_retry(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, body="<html>login</html>")
        device.queue_index(status=303, headers=login_headers())
        device.queue_set(status=200, payload=[{"name": "CAPPL:X", "status": "OK", "value": "1"}])
        result = await api.set_data_multi({"CAPPL:X": 1})
        assert result == {"CAPPL:X": "1"}

    async def test_failed_status_raises(self, api, device):
        api._authenticated = True
        device.queue_set(status=200, payload=[{"name": "CAPPL:X", "status": "ERROR"}])
        with pytest.raises(Exception, match="Set failed"):
            await api.set_data_multi({"CAPPL:X": 1})
