"""Tests for new features added during refactoring."""

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def parser_module(tmp_path, monkeypatch):
    """Setup parser module with temporary paths."""
    status_path = tmp_path / "status.log"
    history_path = tmp_path / "history.json"
    active_path = tmp_path / "active_sessions.json"
    geo_cache_path = tmp_path / "geolocation_cache.json"

    monkeypatch.setenv("OPENVPN_STATUS_LOG", str(status_path))
    monkeypatch.setenv("OPENVPN_HISTORY_LOG", str(history_path))
    monkeypatch.setenv("OPENVPN_ACTIVE_SESSIONS", str(active_path))

    from app import config

    importlib.reload(config)

    from app import parser

    importlib.reload(parser)

    # Set geolocation cache file path
    parser._GEOLOCATION_CACHE_FILE = geo_cache_path

    return parser, status_path, history_path, active_path, geo_cache_path


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Setup Flask test client."""
    history_path = tmp_path / "history.json"

    monkeypatch.setenv("OPENVPN_HISTORY_LOG", str(history_path))

    from app import config

    importlib.reload(config)

    from app import routes

    importlib.reload(routes)

    routes.app.config.update(TESTING=True)
    client = routes.app.test_client()

    return client, history_path


def test_geolocation_caching(parser_module, monkeypatch):
    """Test that geolocation results are cached to avoid redundant API calls."""
    parser, _, _, _, geo_cache_path = parser_module

    # Mock the fetch_geolocation function
    mock_fetch = Mock(
        return_value={
            "city": "TestCity",
            "country": "TestCountry",
            "latitude": 55.7558,
            "longitude": 37.6173,
        }
    )
    monkeypatch.setattr(parser, "fetch_geolocation", mock_fetch)

    # Reset cache
    parser._geolocation_cache.clear()
    parser._geolocation_cache_loaded = False

    # First call - should fetch from API
    result1 = parser.fetch_geolocation_cached("203.0.113.1")
    assert result1["city"] == "TestCity"
    assert mock_fetch.call_count == 1

    # Second call - should use cache
    result2 = parser.fetch_geolocation_cached("203.0.113.1")
    assert result2["city"] == "TestCity"
    assert mock_fetch.call_count == 1  # Still 1 - cache was used

    # Verify cache was saved to disk
    assert geo_cache_path.exists()
    with open(geo_cache_path) as f:
        cache_data = json.load(f)
    assert "203.0.113.1" in cache_data
    assert cache_data["203.0.113.1"]["city"] == "TestCity"


def test_geolocation_cache_persistence(parser_module):
    """Test that geolocation cache persists between process restarts."""
    parser, _, _, _, geo_cache_path = parser_module

    # Create a cache file manually
    cache_data = {
        "198.51.100.10": {
            "city": "CachedCity",
            "country": "CachedCountry",
            "latitude": 40.7128,
            "longitude": -74.0060,
        }
    }
    geo_cache_path.write_text(json.dumps(cache_data))

    # Reset in-memory cache
    parser._geolocation_cache.clear()
    parser._geolocation_cache_loaded = False

    # Should load from disk cache
    result = parser.fetch_geolocation_cached("198.51.100.10")
    assert result["city"] == "CachedCity"
    assert result["country"] == "CachedCountry"


def test_parser_handles_invalid_client_data(parser_module, monkeypatch):
    """Test that parser gracefully handles invalid data in status.log."""
    parser, status_path, history_path, active_path, _ = parser_module

    # Create status log with some invalid entries
    status_path.write_text(
        """
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
alice,198.51.100.10:443,invalid_number,2048,2024-01-01 09:00:00
bob,203.0.113.5:1194,1024,-999,2024-01-01 09:00:00
carol,2001:db8::10:1194,2048,4096,invalid_date
dave,192.0.2.5:443,1024,2048,2024-01-01 10:00:00

ROUTING TABLE
10.8.0.1,alice
10.8.0.2,dave

GLOBAL STATS
""".strip()
    )

    # Mock geolocation to avoid API calls
    monkeypatch.setattr(
        parser,
        "fetch_geolocation_cached",
        lambda ip: {"city": None, "country": None, "latitude": None, "longitude": None},
    )

    # Should only parse valid entry (dave)
    clients, active_sessions = parser.parse_status_log(str(status_path))

    # Only dave should be in the result
    assert len(clients) == 1
    assert clients[0]["common_name"] == "dave"
    assert clients[0]["bytes_received"] == 1024
    assert clients[0]["bytes_sent"] == 2048

    # Active sessions should also only have dave
    assert len(active_sessions) == 1
    assert "dave" in active_sessions


def test_active_sessions_always_have_location(parser_module, monkeypatch):
    """Test that active sessions always include location field."""
    parser, status_path, _, active_path, _ = parser_module

    status_path.write_text(
        """
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
alice,198.51.100.10:443,1024,2048,2024-01-01 09:00:00

ROUTING TABLE
10.8.0.1,alice
""".strip()
    )

    # Mock geolocation
    monkeypatch.setattr(
        parser,
        "fetch_geolocation_cached",
        lambda ip: {
            "city": "TestCity",
            "country": "TestCountry",
            "latitude": 55.7558,
            "longitude": 37.6173,
        },
    )

    clients, active_sessions = parser.parse_status_log(str(status_path))

    # Check that active session has location
    assert "alice" in active_sessions
    assert "location" in active_sessions["alice"]
    assert active_sessions["alice"]["location"]["city"] == "TestCity"


def test_history_api_pagination(app_client):
    """Test that history API supports pagination."""
    client, history_path = app_client

    # Create test history with many entries
    history_entries = [
        {
            "timestamp": f"2024-01-{i:02d} 09:00:00",
            "name": f"client{i}",
            "ip": f"198.51.100.{i}",
            "session_id": f"s{i}",
            "rx": float(i),
            "tx": float(i * 2),
            "vpn_ip": f"10.8.0.{i}",
            "vpn_ipv4": f"10.8.0.{i}",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": f"2024-01-{i:02d} 10:00:00",
        }
        for i in range(1, 26)  # 25 entries
    ]
    history_path.write_text(json.dumps(history_entries))

    # Test default pagination
    response = client.get("/api/history")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entries" in data
    assert "pagination" in data
    assert data["pagination"]["total"] == 25
    assert data["pagination"]["limit"] == 100
    assert data["pagination"]["has_more"] is False

    # Test with limit
    response = client.get("/api/history?limit=10")
    data = json.loads(response.data)
    assert len(data["entries"]) == 10
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["has_more"] is True

    # Test with offset
    response = client.get("/api/history?limit=10&offset=20")
    data = json.loads(response.data)
    assert len(data["entries"]) == 5  # Only 5 remaining
    assert data["pagination"]["offset"] == 20
    assert data["pagination"]["has_more"] is False


def test_history_api_client_filter(app_client):
    """Test that history API can filter by client name."""
    client, history_path = app_client

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
            "vpn_ipv6": "",
            "port": "1194",
            "session_end": "2024-01-02 11:00:00",
        },
        {
            "timestamp": "2024-01-03 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "s3",
            "rx": 5.0,
            "tx": 6.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": "",
            "port": "443",
            "session_end": "2024-01-03 10:00:00",
        },
    ]
    history_path.write_text(json.dumps(history_entries))

    # Filter by alice
    response = client.get("/api/history?client=alice")
    data = json.loads(response.data)
    assert len(data["entries"]) == 2
    assert all(e["name"] == "alice" for e in data["entries"])


def test_history_api_date_filter(app_client):
    """Test that history API can filter by date range."""
    client, history_path = app_client

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
            "timestamp": "2024-01-05 09:00:00",
            "name": "bob",
            "ip": "203.0.113.5",
            "session_id": "s2",
            "rx": 3.0,
            "tx": 4.0,
            "vpn_ip": "10.9.0.2",
            "vpn_ipv4": "10.9.0.2",
            "vpn_ipv6": "",
            "port": "1194",
            "session_end": "2024-01-05 11:00:00",
        },
        {
            "timestamp": "2024-01-10 09:00:00",
            "name": "carol",
            "ip": "2001:db8::10",
            "session_id": "s3",
            "rx": 5.0,
            "tx": 6.0,
            "vpn_ip": "2001:db8::ffff",
            "vpn_ipv4": "",
            "vpn_ipv6": "2001:db8::ffff",
            "port": "1194",
            "session_end": "2024-01-10 10:00:00",
        },
    ]
    history_path.write_text(json.dumps(history_entries))

    # Filter by from_date
    response = client.get("/api/history?from_date=2024-01-05")
    data = json.loads(response.data)
    assert len(data["entries"]) == 2
    assert all(e["timestamp"] >= "2024-01-05" for e in data["entries"])

    # Filter by to_date
    response = client.get("/api/history?to_date=2024-01-05")
    data = json.loads(response.data)
    assert len(data["entries"]) == 2
    assert all(e["timestamp"] <= "2024-01-05 23:59:59" for e in data["entries"])

    # Filter by date range
    response = client.get("/api/history?from_date=2024-01-02&to_date=2024-01-08")
    data = json.loads(response.data)
    assert len(data["entries"]) == 1
    assert data["entries"][0]["name"] == "bob"


def test_validate_active_sessions_adds_location(parser_module):
    """Test that validate_active_sessions adds missing location field."""
    parser, _, _, _, _ = parser_module

    # Session without location field
    sessions = {
        "alice": {
            "ip": "198.51.100.10",
            "vpn_ip": "10.8.0.5",
            "connected_at": "2024-01-01 09:00:00",
            "bytes_received": 1024,
            "bytes_sent": 2048,
            "session_id": "test-session",
        }
    }

    validated = parser.validate_active_sessions(sessions)

    assert "alice" in validated
    assert "location" in validated["alice"]
    assert validated["alice"]["location"] == {
        "city": None,
        "country": None,
        "latitude": None,
        "longitude": None,
    }


def test_validate_active_sessions_preserves_location(parser_module):
    """Test that validate_active_sessions preserves existing location field."""
    parser, _, _, _, _ = parser_module

    # Session with location field
    sessions = {
        "alice": {
            "ip": "198.51.100.10",
            "vpn_ip": "10.8.0.5",
            "connected_at": "2024-01-01 09:00:00",
            "bytes_received": 1024,
            "bytes_sent": 2048,
            "session_id": "test-session",
            "location": {
                "city": "Moscow",
                "country": "Russia",
                "latitude": 55.7558,
                "longitude": 37.6173,
            },
        }
    }

    validated = parser.validate_active_sessions(sessions)

    assert "alice" in validated
    assert validated["alice"]["location"]["city"] == "Moscow"
    assert validated["alice"]["location"]["country"] == "Russia"
