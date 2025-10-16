# parser.py
import datetime
import json
import logging
import os
import tempfile
import threading
import uuid
from contextlib import contextmanager
from ipaddress import ip_address
from pathlib import Path

import fcntl
import pytz
import requests
from .config import (
    ACTIVE_SESSIONS_PATH,
    HISTORY_LOG_PATH,
    LOCAL_TZ,
    STATUS_LOG_PATH,
)


logger = logging.getLogger(__name__)

# Geolocation cache with thread-safe lock
_geolocation_cache = {}
_geolocation_cache_lock = threading.Lock()
_geolocation_cache_loaded = False
_GEOLOCATION_CACHE_FILE = Path("data/geolocation_cache.json")


def format_duration(seconds):
    return str(datetime.timedelta(seconds=seconds))


def validate_active_sessions(data):
    if not isinstance(data, dict):
        return {}

    required_fields = {"ip", "vpn_ip", "connected_at", "bytes_received", "bytes_sent", "session_id"}
    validated = {}

    for common_name, session in data.items():
        if not isinstance(common_name, str) or not isinstance(session, dict):
            continue

        if not required_fields.issubset(session.keys()):
            continue

        try:
            bytes_received = int(session["bytes_received"])
            bytes_sent = int(session["bytes_sent"])
        except (TypeError, ValueError):
            continue

        # Ensure location field is present and valid
        location = session.get("location")
        if not isinstance(location, dict):
            location = {"city": None, "country": None, "latitude": None, "longitude": None}

        validated[common_name] = {
            **session,
            "bytes_received": bytes_received,
            "bytes_sent": bytes_sent,
            "location": location,
        }

    return validated


def load_active_sessions(path: str = ACTIVE_SESSIONS_PATH):
    target_path = os.path.abspath(path)

    if os.path.exists(target_path):
        try:
            with open(target_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

        return validate_active_sessions(data)
    return {}


def save_active_sessions(sessions, path: str = ACTIVE_SESSIONS_PATH):
    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    tmp_file_name = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=directory, delete=False) as tmp_file:
            tmp_file_name = tmp_file.name
            json.dump(sessions, tmp_file, ensure_ascii=False, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        os.replace(tmp_file_name, target_path)
    except Exception:
        # Clean up temporary file if something went wrong
        if tmp_file_name and os.path.exists(tmp_file_name):
            try:
                os.unlink(tmp_file_name)
            except OSError:
                pass
        raise


@contextmanager
def history_log(path: str = HISTORY_LOG_PATH):
    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    with open(target_path, "a+") as logf:
        fcntl.flock(logf, fcntl.LOCK_EX)
        try:
            logf.seek(0)
            try:
                entries = json.load(logf)
            except (json.JSONDecodeError, OSError):
                entries = []

            if not isinstance(entries, list):
                entries = []

            yield entries

            logf.seek(0)
            logf.truncate()
            json.dump(entries, logf, ensure_ascii=False, indent=2)
            logf.write("\n")
            logf.flush()
            os.fsync(logf.fileno())
        finally:
            fcntl.flock(logf, fcntl.LOCK_UN)


@contextmanager
def active_sessions_lock(path: str = ACTIVE_SESSIONS_PATH):
    """Prevent concurrent modifications of the active sessions state."""

    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    lock_path = f"{target_path}.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _split_real_address(address: str):
    if not address:
        return "", ""

    value = address.strip()

    if value.startswith("["):
        if "]:" in value:
            ip_part, port_part = value.split("]:", 1)
            return ip_part.lstrip("["), port_part
        return value.strip("[]"), ""

    try:
        ip_address(value)
        return value, ""
    except ValueError:
        if ":" in value:
            ip_part, port_part = value.rsplit(":", 1)
            if port_part.isdigit():
                try:
                    ip_address(ip_part)
                    return ip_part, port_part
                except ValueError:
                    pass
        return value, ""


def fetch_geolocation(ip: str):
    """
    Fetch geolocation data for an IP address using ip-api.com

    Returns dict with city, country, latitude, longitude or None values on error
    """
    if not ip:
        return {"city": None, "country": None, "latitude": None, "longitude": None}

    try:
        # Using ip-api.com free service (no API key required)
        # Limit: 45 requests per minute from an IP address
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)

        if response.status_code == 200:
            data = response.json()

            if data.get("status") == "success":
                return {
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
    except Exception as e:
        logger.warning(f"Failed to fetch geolocation for {ip}: {e}")

    return {"city": None, "country": None, "latitude": None, "longitude": None}


def _load_geolocation_cache():
    """Load geolocation cache from disk."""
    if _GEOLOCATION_CACHE_FILE.exists():
        try:
            with open(_GEOLOCATION_CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load geolocation cache: {e}")
            return {}
    return {}


def _save_geolocation_cache():
    """Save geolocation cache to disk."""
    try:
        _GEOLOCATION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_GEOLOCATION_CACHE_FILE, "w") as f:
            json.dump(_geolocation_cache, f, indent=2)
    except OSError as e:
        logger.warning(f"Failed to save geolocation cache: {e}")


def fetch_geolocation_cached(ip: str):
    """
    Fetch geolocation with in-memory and persistent caching.

    Cache is kept in memory for the lifetime of the process and persisted to disk.
    This dramatically reduces API calls when clients reconnect with the same IP.

    Args:
        ip: IP address to look up

    Returns:
        dict with city, country, latitude, longitude (or None values on error)
    """
    global _geolocation_cache_loaded

    if not ip:
        return {"city": None, "country": None, "latitude": None, "longitude": None}

    # Lazy load cache from disk on first use
    with _geolocation_cache_lock:
        if not _geolocation_cache_loaded:
            loaded_cache = _load_geolocation_cache()
            _geolocation_cache.update(loaded_cache)
            _geolocation_cache_loaded = True
            if loaded_cache:
                logger.info(f"Loaded {len(loaded_cache)} geolocation entries from cache")

        # Check in-memory cache
        if ip in _geolocation_cache:
            logger.debug(f"Geolocation cache hit for {ip}")
            return _geolocation_cache[ip]

    # Cache miss - fetch from API
    logger.info(f"Fetching geolocation for {ip} (cache miss)")
    location = fetch_geolocation(ip)

    # Save to cache (both memory and disk)
    with _geolocation_cache_lock:
        _geolocation_cache[ip] = location
        _save_geolocation_cache()

    return location


def _should_skip_undef_session(common_name, connected_at, session_end, rx, tx):
    """
    Check if session should be skipped (Variant 4: short UNDEF sessions).

    Skip sessions that are:
    - Named "UNDEF"
    - Duration < 10 seconds
    - Traffic < 0.1 MB total
    """
    if common_name != "UNDEF":
        return False

    # If session_end is None (session just started), don't skip yet
    if not session_end or not connected_at:
        return False

    try:
        start_dt = datetime.datetime.strptime(connected_at, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.datetime.strptime(session_end, "%Y-%m-%d %H:%M:%S")
        start_dt = LOCAL_TZ.localize(start_dt)
        end_dt = LOCAL_TZ.localize(end_dt)
        duration_seconds = (end_dt - start_dt).total_seconds()

        # Check if session is short and has minimal traffic
        if duration_seconds < 10 and (rx or 0) + (tx or 0) < 0.1:
            logger.info(
                f"Skipping UNDEF session: duration={duration_seconds}s, rx={rx}MB, tx={tx}MB"
            )
            return True
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing session times: {e}")
        pass

    return False


def _complete_session(session, common_name, disconnect_time):
    """
    Complete a session and add it to history.
    Simple, straightforward function - all sessions go through here when they end.

    Args:
        session: Session dict from active_sessions
        common_name: Client common name
        disconnect_time: Disconnection timestamp string
    """
    rx = round(session["bytes_received"] / (1024 * 1024), 2)
    tx = round(session["bytes_sent"] / (1024 * 1024), 2)

    # Skip short UNDEF sessions with minimal traffic
    if _should_skip_undef_session(
        common_name,
        session["connected_at"],
        disconnect_time,
        rx,
        tx,
    ):
        logger.info(f"Skipping short UNDEF session for {common_name}")
        return

    vpn_ip = session.get("vpn_ip") or ""
    port = session.get("port") or ""
    vpn_ipv4 = session.get("vpn_ipv4") or ""
    vpn_ipv6 = session.get("vpn_ipv6") or ""

    # Ensure vpn_ipv4/vpn_ipv6 are populated from vpn_ip if needed
    if not vpn_ipv4 and not vpn_ipv6 and vpn_ip:
        try:
            ip_obj = ip_address(vpn_ip)
            if ip_obj.version == 4:
                vpn_ipv4 = vpn_ip
            else:
                vpn_ipv6 = vpn_ip
        except ValueError:
            pass

    # Simply add completed session to history
    with history_log() as entries:
        entries.append(
            {
                "timestamp": session["connected_at"],
                "name": common_name,
                "ip": session.get("ip"),
                "session_id": session["session_id"],
                "rx": rx,
                "tx": tx,
                "vpn_ip": vpn_ip or None,
                "vpn_ipv4": vpn_ipv4 or None,
                "vpn_ipv6": vpn_ipv6 or None,
                "port": port or None,
                "session_end": disconnect_time,
                "location": session.get(
                    "location",
                    {
                        "city": None,
                        "country": None,
                        "latitude": None,
                        "longitude": None,
                    },
                ),
            }
        )

    logger.info(f"Completed session for {common_name}: {rx}MB rx, {tx}MB tx")


def parse_status_log(filepath=STATUS_LOG_PATH):
    clients = []
    active_sessions_result = {}
    current_common_names = set()
    vpn_ip_map = {}
    new_sessions = []
    client_records = []

    try:
        with active_sessions_lock():
            active_sessions = load_active_sessions()
            now = datetime.datetime.now(LOCAL_TZ)

            with open(filepath, "r") as f:
                section = None

                for raw_line in f:
                    line = raw_line.strip()

                    if raw_line.startswith(
                        "Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since"
                    ):
                        section = "clients"
                        continue

                    if raw_line.startswith("ROUTING TABLE"):
                        section = "routing"
                        continue

                    if raw_line.startswith("GLOBAL STATS"):
                        section = None
                        continue

                    if not line:
                        if section in {"clients", "routing"}:
                            section = None
                        continue

                    if section == "routing":
                        parts = line.split(",")
                        if len(parts) >= 2:
                            vpn_ip = parts[0].strip()
                            common_name = parts[1].strip()

                            entry = vpn_ip_map.setdefault(common_name, {"ipv4": None, "ipv6": None})

                            try:
                                ip_obj = ip_address(vpn_ip)
                            except ValueError:
                                # Fallback to the previous behaviour – store the value in the
                                # first available slot so we don't lose potentially useful
                                # information even if it isn't a valid IP.
                                if entry["ipv4"] is None:
                                    entry["ipv4"] = vpn_ip
                                elif entry["ipv6"] is None:
                                    entry["ipv6"] = vpn_ip
                                continue

                            if ip_obj.version == 4:
                                entry["ipv4"] = vpn_ip
                            else:
                                entry["ipv6"] = vpn_ip
                        continue

                    if section == "clients":
                        parts = line.split(",")
                        if len(parts) < 5:
                            continue

                        try:
                            common_name = parts[0]
                            real_ip, port = _split_real_address(parts[1])
                            bytes_received = int(parts[2])
                            bytes_sent = int(parts[3])
                            connected_since = parts[4]

                            # Validate byte counts
                            if bytes_received < 0 or bytes_sent < 0:
                                raise ValueError("Negative byte count")

                            # Convert UTC time from status.log to LOCAL_TZ
                            # status.log always contains UTC timestamps
                            utc_dt = datetime.datetime.strptime(connected_since, "%Y-%m-%d %H:%M:%S")
                            utc_dt = pytz.UTC.localize(utc_dt)
                            connected_dt = utc_dt.astimezone(LOCAL_TZ)
                            time_online = format_duration(int((now - connected_dt).total_seconds()))
                        except (ValueError, IndexError) as e:
                            logger.warning(
                                f"Invalid client data in status.log: {line.strip()} - Error: {e}"
                            )
                            continue

                        client_records.append(
                            {
                                "common_name": common_name,
                                "real_ip": real_ip,
                                "port": port,
                                "bytes_received": bytes_received,
                                "bytes_sent": bytes_sent,
                                "connected_since": connected_since,
                                "time_online": time_online,
                            }
                        )

                        current_common_names.add(common_name)

                        if common_name not in active_sessions:
                            session_id = str(uuid.uuid4())
                            # Fetch geolocation for new session (with caching)
                            location = fetch_geolocation_cached(real_ip)
                            active_sessions[common_name] = {
                                "ip": real_ip,
                                "vpn_ip": None,
                                "vpn_ipv4": None,
                                "vpn_ipv6": None,
                                "connected_at": connected_dt.strftime("%Y-%m-%d %H:%M:%S"),
                                "bytes_received": bytes_received,
                                "bytes_sent": bytes_sent,
                                "port": port,
                                "session_id": session_id,
                                "location": location,
                            }
                            new_sessions.append(common_name)
                        else:
                            # Check if client reconnected (connected_since changed)
                            stored_connected_at = active_sessions[common_name].get("connected_at")
                            current_connected_at = connected_dt.strftime("%Y-%m-%d %H:%M:%S")

                            if stored_connected_at != current_connected_at:
                                # Client reconnected - close old session and create new one
                                old_session = active_sessions[common_name]
                                disconnect_time = now.strftime("%Y-%m-%d %H:%M:%S")

                                # Complete the old session
                                _complete_session(old_session, common_name, disconnect_time)

                                # Create new session
                                session_id = str(uuid.uuid4())
                                # Fetch geolocation for new session (with caching)
                                location = fetch_geolocation_cached(real_ip)
                                active_sessions[common_name] = {
                                    "ip": real_ip,
                                    "vpn_ip": None,
                                    "vpn_ipv4": None,
                                    "vpn_ipv6": None,
                                    "connected_at": current_connected_at,
                                    "bytes_received": bytes_received,
                                    "bytes_sent": bytes_sent,
                                    "port": port,
                                    "session_id": session_id,
                                    "location": location,
                                }
                                new_sessions.append(common_name)
                            else:
                                # Same session - just update stats
                                active_sessions[common_name]["bytes_received"] = bytes_received
                                active_sessions[common_name]["bytes_sent"] = bytes_sent
                                active_sessions[common_name]["ip"] = real_ip
                                active_sessions[common_name]["port"] = port

            for record in client_records:
                common_name = record["common_name"]
                vpn_ip_entry = vpn_ip_map.get(common_name, {})
                vpn_ipv4 = vpn_ip_entry.get("ipv4") if isinstance(vpn_ip_entry, dict) else None
                vpn_ipv6 = vpn_ip_entry.get("ipv6") if isinstance(vpn_ip_entry, dict) else None

                vpn_ip = vpn_ipv4 or vpn_ipv6

                record["vpn_ip"] = vpn_ip
                record["vpn_ipv4"] = vpn_ipv4
                record["vpn_ipv6"] = vpn_ipv6
                clients.append(record)

                if common_name in active_sessions:
                    active_sessions[common_name]["vpn_ip"] = vpn_ip
                    active_sessions[common_name]["vpn_ipv4"] = vpn_ipv4
                    active_sessions[common_name]["vpn_ipv6"] = vpn_ipv6

            # Update VPN IPs for new sessions (already in active_sessions)
            # No need to add to history - they'll be added when they disconnect
            for common_name in new_sessions:
                session = active_sessions.get(common_name)
                if not session:
                    continue

                vpn_ip_entry = vpn_ip_map.get(common_name)
                if isinstance(vpn_ip_entry, dict):
                    vpn_ipv4 = vpn_ip_entry.get("ipv4") or ""
                    vpn_ipv6 = vpn_ip_entry.get("ipv6") or ""
                else:
                    value = vpn_ip_entry or ""
                    vpn_ipv4 = value
                    vpn_ipv6 = ""
                    try:
                        if value:
                            ip_obj = ip_address(value)
                            if ip_obj.version == 6:
                                vpn_ipv4, vpn_ipv6 = "", value
                    except ValueError:
                        pass
                vpn_ip = vpn_ipv4 or vpn_ipv6 or ""

                session["vpn_ip"] = vpn_ip or None
                session["vpn_ipv4"] = vpn_ipv4 or None
                session["vpn_ipv6"] = vpn_ipv6 or None

            # Handle disconnected clients
            disconnected = [cn for cn in list(active_sessions) if cn not in current_common_names]
            for cn in disconnected:
                session = active_sessions[cn]
                disconnect_time = now.strftime("%Y-%m-%d %H:%M:%S")

                # Complete the session
                _complete_session(session, cn, disconnect_time)

                # Remove from active sessions
                del active_sessions[cn]

            save_active_sessions(active_sessions)
            # Store copy for return value (outside the lock context)
            active_sessions_result = dict(active_sessions)
    except Exception:  # pragma: no cover - safeguard logging
        logger.exception("Error parsing status log")

    return clients, active_sessions_result
