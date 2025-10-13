import importlib
import json
import sys
from datetime import datetime as RealDateTime
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def parser_module(tmp_path, monkeypatch):
    status_path = tmp_path / "status.log"
    history_path = tmp_path / "history.json"
    active_path = tmp_path / "active_sessions.json"

    monkeypatch.setenv("OPENVPN_STATUS_LOG", str(status_path))
    monkeypatch.setenv("OPENVPN_HISTORY_LOG", str(history_path))
    monkeypatch.setenv("OPENVPN_ACTIVE_SESSIONS", str(active_path))

    from app import config

    importlib.reload(config)

    from app import parser

    importlib.reload(parser)

    return parser, status_path, history_path, active_path


def _freeze_time(
    monkeypatch,
    parser,
    year=2024,
    month=1,
    day=1,
    hour=12,
    minute=0,
    second=0,
):
    class FixedDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(year, month, day, hour, minute, second, tzinfo=tz)

    monkeypatch.setattr(parser.datetime, "datetime", FixedDateTime)
    return FixedDateTime


def test_parse_status_log_records_disconnect(parser_module, monkeypatch):
    parser, status_path, history_path, active_path = parser_module

    parser.save_active_sessions(
        {
            "alice": {
                "ip": "198.51.100.10",
                "vpn_ip": "10.8.0.5",
                "connected_at": "2024-01-01 09:00:00",
                "bytes_received": 1048576,
                "bytes_sent": 2097152,
                "session_id": "existing-session",
                "port": "443",
            }
        },
        str(active_path),
    )

    status_path.write_text(
        """
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since

ROUTING TABLE
""".strip()
    )

    _freeze_time(monkeypatch, parser, hour=13)

    clients, active_sessions = parser.parse_status_log(str(status_path))
    assert clients == []
    assert active_sessions == {}

    with active_path.open() as fh:
        data = json.load(fh)
    assert data == {}

    history_entries = json.loads(history_path.read_text())
    assert history_entries == [
        {
            "timestamp": "2024-01-01 09:00:00",
            "name": "alice",
            "ip": "198.51.100.10",
            "session_id": "existing-session",
            "rx": 1.0,
            "tx": 2.0,
            "vpn_ip": "10.8.0.5",
            "vpn_ipv4": "10.8.0.5",
            "vpn_ipv6": None,
            "port": "443",
            "session_end": "2024-01-01 13:00:00",
            "location": {"city": None, "country": None, "latitude": None, "longitude": None},
        }
    ]


def test_save_active_sessions_cleans_up_temp_file_on_error(parser_module, monkeypatch):
    """Test that temporary files are cleaned up when os.replace() fails."""
    parser, _, _, active_path = parser_module

    test_data = {
        "client1": {
            "ip": "192.168.1.1",
            "vpn_ip": "10.8.0.2",
            "connected_at": "2024-01-01 12:00:00",
            "bytes_received": 1024,
            "bytes_sent": 2048,
            "session_id": "test-session-id",
            "port": "443",
        }
    }

    # Mock os.replace to fail
    original_replace = parser.os.replace

    def failing_replace(src, dst):
        # Store the temp file name before it would be replaced
        temp_files = list(active_path.parent.glob("tmp*"))
        if temp_files:
            raise OSError("Simulated failure")
        original_replace(src, dst)

    monkeypatch.setattr(parser.os, "replace", failing_replace)

    # Try to save and expect it to fail
    with pytest.raises(OSError, match="Simulated failure"):
        parser.save_active_sessions(test_data, str(active_path))

    # Verify no temporary files are left behind
    temp_files = list(active_path.parent.glob("tmp*"))
    assert len(temp_files) == 0, f"Found unexpected temp files: {temp_files}"


def test_save_active_sessions_success_leaves_no_temp_files(parser_module):
    """Test that successful save operations don't leave temp files."""
    parser, _, _, active_path = parser_module

    test_data = {
        "client1": {
            "ip": "192.168.1.1",
            "vpn_ip": "10.8.0.2",
            "connected_at": "2024-01-01 12:00:00",
            "bytes_received": 1024,
            "bytes_sent": 2048,
            "session_id": "test-session-id",
            "port": "443",
        }
    }

    # Save successfully
    parser.save_active_sessions(test_data, str(active_path))

    # Verify no temporary files are left behind
    temp_files = list(active_path.parent.glob("tmp*"))
    assert len(temp_files) == 0, f"Found unexpected temp files: {temp_files}"

    # Verify the data was saved correctly
    with active_path.open() as f:
        saved_data = json.load(f)
    assert saved_data == test_data
