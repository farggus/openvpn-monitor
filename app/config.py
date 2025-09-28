"""Application configuration helpers for log parsing and API."""

import os

import pytz

_DEFAULT_TIMEZONE = "Europe/Bucharest"


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


LOCAL_TZ = _load_timezone()
STATUS_LOG_PATH = _load_path("OPENVPN_STATUS_LOG", "/var/log/openvpn/status.log")
HISTORY_LOG_PATH = _load_path("OPENVPN_HISTORY_LOG", "/var/log/openvpn/session_history.log")
ACTIVE_SESSIONS_PATH = _load_path(
    "OPENVPN_ACTIVE_SESSIONS", "/var/log/openvpn/active_sessions.json"
)
SERVER_STATUS_PATH = _load_path("OPENVPN_SERVER_STATUS", "/var/log/openvpn/server_status.json")
CLIENT_GEO_DB_PATH = _load_path(
    "OPENVPN_CLIENT_GEO_DB", "/var/log/openvpn/client_geolocation.json"
)
