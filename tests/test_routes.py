import importlib
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    geo_path = tmp_path / "client_geo.json"

    monkeypatch.setenv("OPENVPN_HISTORY_LOG", str(history_path))
    monkeypatch.setenv("OPENVPN_CLIENT_GEO_DB", str(geo_path))

    from app import config

    importlib.reload(config)

    from app import geo_store, routes

    importlib.reload(geo_store)
    importlib.reload(routes)

    routes.app.config.update(TESTING=True)
    client = routes.app.test_client()

    return client, history_path, geo_path


def test_api_history_includes_vpn_ip_versions(app_client):
    client, history_path, _ = app_client

    history_entries = [
        {
            "timestamp": "2024-01-01 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s1",
            "rx": 1.0,
            "tx": 2.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-01 10:00:00",
        },
        {
            "timestamp": "2024-01-02 09:00:00",
            "name": "bob",
            "ip": "203.0.113.5",
            "session_id": "s2",
            "rx": 3.0,
            "tx": 4.0,
            "vpn_ip": "10.9.0.2",
            "vpn_ipv4": "10.9.0.2",
            "vpn_ipv6": "2001:db8::abcd",
            "port": "1194",
            "session_end": "2024-01-02 11:00:00",
        },
        {
            "timestamp": "2024-01-03 09:00:00",
            "name": "carol",
            "ip": "2001:db8::10",
            "session_id": "s3",
            "rx": 5.0,
            "tx": 6.0,
            "vpn_ip": "2001:db8::ffff",
            "vpn_ipv4": "",
            "vpn_ipv6": "2001:db8::ffff",
            "port": "1194",
            "session_end": "2024-01-03 10:00:00",
        },
    ]
    history_path.write_text(json.dumps(history_entries))

    response = client.get("/api/history")
    assert response.status_code == 200

    entries = json.loads(response.data)
    assert len(entries) == 3

    alice, bob, carol = entries

    assert alice["vpn_ip"] == "10.8.0.5"
    assert alice["vpn_ipv4"] == "10.8.0.5"
    assert alice["vpn_ipv6"] == ""

    assert bob["vpn_ip"] == "10.9.0.2"
    assert bob["vpn_ipv4"] == "10.9.0.2"
    assert bob["vpn_ipv6"] == "2001:db8::abcd"

    assert carol["vpn_ip"] == "2001:db8::ffff"
    assert carol["vpn_ipv4"] == ""
    assert carol["vpn_ipv6"] == "2001:db8::ffff"


def test_geo_db_populated_from_history(app_client):
    client, history_path, geo_path = app_client

    history_entries = [
        {
            "timestamp": "2024-01-01 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s1",
            "rx": 1.0,
            "tx": 2.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-01 10:00:00",
        },
        {
            "timestamp": "2024-01-03 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s2",
            "rx": 1.0,
            "tx": 2.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-03 11:00:00",
        },
        {
            "timestamp": "2024-01-02 09:00:00",
            "name": "bob",
            "ip": "203.0.113.5",
            "session_id": "s3",
            "rx": 3.0,
            "tx": 4.0,
            "vpn_ip": "10.9.0.2",
            "vpn_ipv4": "10.9.0.2",
            "vpn_ipv6": "2001:db8::abcd",
            "port": "1194",
            "session_end": "2024-01-02 11:00:00",
        },
    ]
    history_path.write_text(json.dumps(history_entries))

    response = client.get("/api/history")
    assert response.status_code == 200

    assert geo_path.exists()

    payload = json.loads(geo_path.read_text())
    clients = payload["clients"]

    assert set(clients.keys()) == {"alice", "bob"}

    alice = clients["alice"]
    assert alice["first_seen"] == "2024-01-01 09:00:00"
    assert alice["last_seen"] == "2024-01-03 09:00:00"
    alice_ip = alice["ips"]["198.51.100.10"]
    assert alice_ip["vpn_ipv4"] == ["10.8.0.5"]
    assert alice_ip["vpn_ipv6"] == []
    assert alice_ip["location"] == {
        "latitude": None,
        "longitude": None,
        "city": "",
        "country": "",
    }

    bob = clients["bob"]
    assert bob["first_seen"] == "2024-01-02 09:00:00"
    bob_ip = bob["ips"]["203.0.113.5"]
    assert bob_ip["vpn_ipv6"] == ["2001:db8::abcd"]


def test_clients_summary_counts_closed_sessions(app_client, monkeypatch):
    client, history_path, _ = app_client

    history_entries = [
        {
            "timestamp": "2024-01-01 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s1",
            "rx": None,
            "tx": None,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": None,
        },
        {
            "timestamp": "2024-01-01 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s1",
            "rx": 1.0,
            "tx": 2.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-01 10:00:00",
        },
        {
            "timestamp": "2024-01-02 11:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s2",
            "rx": 3.0,
            "tx": 4.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-02 12:00:00",
        },
    ]
    history_path.write_text(json.dumps(history_entries))

    from app import routes

    monkeypatch.setattr(routes, "parse_status_log", lambda: [])

    response = client.get("/api/clients/summary")
    assert response.status_code == 200

    payload = json.loads(response.data)
    assert payload["clients"][0]["sessions"] == 2


def test_clients_summary_includes_active_session(app_client, monkeypatch):
    client, history_path, _ = app_client

    history_entries = [
        {
            "timestamp": "2024-01-01 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s1",
            "rx": 1.0,
            "tx": 2.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-01 10:00:00",
        }
    ]
    history_path.write_text(json.dumps(history_entries))

    active_clients = [
        {
            "common_name": "alice",
            "connected_since": "2024-01-02 09:00:00",
            "time_online": "01:00:00",
            "real_ip": "198.51.100.10",
            "port": "443",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "bytes_received": 1024,
            "bytes_sent": 2048,
        }
    ]

    from app import routes

    monkeypatch.setattr(routes, "parse_status_log", lambda: active_clients)

    response = client.get("/api/clients/summary")
    assert response.status_code == 200

    payload = json.loads(response.data)
    assert payload["clients"][0]["sessions"] == 2
    assert payload["clients"][0]["is_online"] is True
