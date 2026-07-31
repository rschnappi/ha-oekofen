"""Tests for circuit/unit discovery (discovery.py)."""
from unittest.mock import AsyncMock

from custom_components.oekofen.discovery import (
    FALLBACK_CIRCUITS,
    async_discover_circuits,
)


def _presence_response(hk=(0,), ww=(0,), zirkp=(), pellematic=(0,)):
    data = {}
    for i in range(6):
        data[f"CAPPL:LOCAL.hk[{i}].vorhanden"] = {"value": "1" if i in hk else "0"}
    for i in range(3):
        data[f"CAPPL:LOCAL.ww[{i}].vorhanden"] = {"value": "1" if i in ww else "0"}
    for i in range(3):
        data[f"CAPPL:LOCAL.zirkp[{i}].vorhanden"] = {"value": "1" if i in zirkp else "0"}
    for i in range(4):
        data[f"CAPPL:LOCAL.pellematic_vorhanden[{i}]"] = {"value": "1" if i in pellematic else "0"}
    return data


async def test_discovers_present_circuits():
    api = AsyncMock()
    api.get_data.return_value = _presence_response(hk=(0, 1), ww=(0,), pellematic=(0,))

    circuits = await async_discover_circuits(api)

    assert circuits["hk"] == [0, 1]
    assert circuits["ww"] == [0]
    assert circuits["zirkp"] == []
    assert circuits["pellematic"] == [0]


async def test_probes_the_expected_parameters():
    api = AsyncMock()
    api.get_data.return_value = _presence_response()

    await async_discover_circuits(api)

    probed = api.get_data.call_args[0][0]
    assert "CAPPL:LOCAL.hk[0].vorhanden" in probed
    assert "CAPPL:LOCAL.hk[5].vorhanden" in probed
    assert "CAPPL:LOCAL.ww[2].vorhanden" in probed
    assert "CAPPL:LOCAL.pellematic_vorhanden[3]" in probed


async def test_falls_back_on_api_error():
    api = AsyncMock()
    api.get_data.side_effect = Exception("device unreachable")

    circuits = await async_discover_circuits(api)

    assert circuits == FALLBACK_CIRCUITS


async def test_falls_back_when_nothing_present():
    api = AsyncMock()
    api.get_data.return_value = _presence_response(hk=(), ww=(), zirkp=(), pellematic=())

    circuits = await async_discover_circuits(api)

    assert circuits == FALLBACK_CIRCUITS


async def test_missing_or_malformed_value_treated_as_absent():
    api = AsyncMock()
    data = _presence_response(hk=(0,))
    data["CAPPL:LOCAL.hk[0].vorhanden"] = {"value": "not-a-number"}
    api.get_data.return_value = data

    circuits = await async_discover_circuits(api)

    assert 0 not in circuits["hk"]
