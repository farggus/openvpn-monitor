"""Application configuration helpers for log parsing and API."""

import json
import os
from pathlib import Path

import pytz

_DEFAULT_TIMEZONE = "Europe/Bucharest"
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "data"


def _load_timezone():
    tz_name = os.getenv("OPENVPN_MONITOR_TZ", _DEFAULT_TIMEZONE)
    try:
        return pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        # Fallback to default to keep the application running.
        return pytz.timezone(_DEFAULT_TIMEZONE)


def _load_path(env_var: str, default: str) -> str:
    path = os.getenv(env_var, default)
    return os.path.expanduser(path)


def _default_data_path(filename: str) -> str:
    return str(_DEFAULT_DATA_DIR / filename)


def _ensure_data_files(targets) -> None:
    for raw_path, payload in targets.items():
        path = Path(raw_path)
        directory = path.parent
        if directory:
            directory.mkdir(parents=True, exist_ok=True)

        if path.exists():
            continue

        if payload is None:
            path.touch()
            continue

        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


LOCAL_TZ = _load_timezone()
STATUS_LOG_PATH = _load_path("OPENVPN_STATUS_LOG", "/var/log/openvpn/status.log")
HISTORY_LOG_PATH = _load_path("OPENVPN_HISTORY_LOG", _default_data_path("session_history.json"))
ACTIVE_SESSIONS_PATH = _load_path(
    "OPENVPN_ACTIVE_SESSIONS", _default_data_path("active_sessions.json")
)
SERVER_STATUS_PATH = _load_path("OPENVPN_SERVER_STATUS", _default_data_path("server_status.json"))
CLIENT_GEO_DB_PATH = _load_path(
    "OPENVPN_CLIENT_GEO_DB", _default_data_path("client_geolocation.json")
)

_ensure_data_files(
    {
        HISTORY_LOG_PATH: [],
        ACTIVE_SESSIONS_PATH: {},
        SERVER_STATUS_PATH: {},
        CLIENT_GEO_DB_PATH: {"clients": {}, "updated_at": None},
    }
)
