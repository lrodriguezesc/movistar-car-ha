import json
from pathlib import Path

import pytest

from movistar_car.api import MovistarCarAPI, _bytes_to_mb, _parse_json, _to_number

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "session.json").read_text())
LOCATION = {
    "Status": [
        {
            "ServiceId": 10,
            "TotalKilometers": 973.6,
            "OnStreetParkingStatus": 0,
            "LatestEvent": {
                "Latitude": 40.0,
                "Longitude": -3.0,
                "ValidPosition": True,
                "Speed": 0.0,
                "Fuel": 80.0,
                "Heading": 158,
                "Date": 1700000000000,
                "EventType": 5002,
            },
        }
    ]
}


@pytest.fixture
def api(monkeypatch):
    a = MovistarCarAPI("user", "pass", tank_capacity=50)
    monkeypatch.setattr(a, "authenticate", lambda: FIXTURE)
    monkeypatch.setattr(a, "get_location", lambda i: LOCATION)
    monkeypatch.setattr(a, "get_obd_codes", lambda s: [{"Solved": False}, {"Solved": True}])
    return a


def test_converters():
    assert _to_number("89") == 89.0
    assert _to_number(None) is None
    assert _to_number("x") is None
    assert _parse_json('{"a": 1}') == {"a": 1}
    assert _parse_json("not json") is None
    assert _parse_json(None) is None
    assert _bytes_to_mb(1048576) == 1.0
    assert _bytes_to_mb(None) is None


def test_vehicle_and_service_data(api):
    d = api.get_all_data(0, 10)
    assert (d["vehicle_make"], d["vehicle_model"], d["vehicle_year"]) == ("OPEL", "CORSA", 2014)
    assert d["avg_consumption"] == 5.1
    assert d["scoring_daily"] == 89.0
    assert d["scoring_monthly"]["2026"][:3] == [82, 94, 99]
    assert d["alarm_armed"] is False


def test_wifi_uses_service_pack_not_device(api):
    d = api.get_all_data(0, 10)
    # Device-level values are 14.4 and 0. The real pack is on the service.
    assert d["wifi_pack_size_mb"] == 20480.0
    assert d["wifi_pack_used_mb"] == 2.96
    assert d["wifi_pack_expiry"] == 1794956400000


def test_fuel_litres_and_certified_range_use_tank_capacity(api):
    d = api.get_all_data(0, 10)
    assert d["fuel_liters"] == 40.0  # 80 % of 50 L
    assert d["range_estimate"] == round(40.0 / 5.1 * 100)


def test_obd_errors_count_unsolved_only(api):
    d = api.get_all_data(0, 10)
    assert d["errors"] is True
    assert d["error_count"] == 1


def test_service_found_by_device_id_when_service_id_unknown(api):
    d = api.get_all_data(0, 0)  # service_id 0 does not match, DeviceId does
    assert d["vehicle_model"] == "CORSA"


def test_missing_service_does_not_crash(monkeypatch):
    a = MovistarCarAPI("u", "p")
    monkeypatch.setattr(a, "authenticate", lambda: {"Devices": FIXTURE["Devices"]})
    monkeypatch.setattr(a, "get_location", lambda i: LOCATION)
    monkeypatch.setattr(a, "get_obd_codes", lambda s: [])
    d = a.get_all_data(0, 10)
    assert d["vehicle_model"] is None
    assert d["scoring_daily"] is None
    assert d["wifi_pack_size_mb"] is None
