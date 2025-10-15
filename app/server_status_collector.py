"""
Server status collection module that works from inside Docker container.

Collects server status information without requiring host access:
- Status: Determined by checking status.log freshness
- Up Since: Container start time (from /proc/1)
- Public IP: Fetched via external APIs
- Pingable: Pings public IP
- Local IP: From environment variable or container network interface

No cron required - runs from logger.py background process.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from .config import LOCAL_TZ, SERVER_STATUS_PATH, STATUS_LOG_PATH

logger = logging.getLogger(__name__)


def get_status_log_update_time():
    """
    Get the last update time from status.log.

    OpenVPN status.log format version 3 includes:
    Updated,<timestamp>

    Returns:
        datetime object or None if not found
    """
    try:
        with open(STATUS_LOG_PATH, "r") as f:
            for line in f:
                if line.startswith("Updated,"):
                    timestamp_str = line.strip().split(",", 1)[1]
                    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.warning(f"Failed to parse Updated timestamp from status.log: {e}")

    return None


def get_status_log_modified_time():
    """
    Get status.log file modification time as fallback.

    Returns:
        datetime object or None
    """
    try:
        stat_result = os.stat(STATUS_LOG_PATH)
        return datetime.fromtimestamp(stat_result.st_mtime)
    except Exception as e:
        logger.warning(f"Failed to get status.log mtime: {e}")

    return None


def get_container_start_time():
    """
    Get container start time by checking /proc/1/ (PID 1 = supervisord).

    This gives us the exact time when the Docker container started.
    Time is converted from UTC to configured timezone (LOCAL_TZ).

    Returns:
        datetime object in LOCAL_TZ or None
    """
    try:
        import pytz

        # PID 1 is supervisord, which starts when container starts
        stat_result = os.stat("/proc/1")

        # /proc/1 timestamp is in UTC
        start_time_utc = datetime.fromtimestamp(stat_result.st_mtime, tz=pytz.UTC)

        # Convert to configured timezone
        start_time_local = start_time_utc.astimezone(LOCAL_TZ)

        # Return as naive datetime (without timezone info) for consistency
        return start_time_local.replace(tzinfo=None)
    except Exception as e:
        logger.warning(f"Failed to get container start time from /proc/1: {e}")
        return None


def check_server_status():
    """
    Check if OpenVPN server is running by checking status.log freshness.

    If status.log was updated in the last 30 seconds, consider server CONNECTED.
    Uses container start time (from /proc/1) as uptime.

    Returns:
        tuple: (status_string, uptime_string)
    """
    # Try to get Updated timestamp from status.log
    updated_time = get_status_log_update_time()

    # Fallback to file mtime if Updated timestamp not found
    if not updated_time:
        updated_time = get_status_log_modified_time()

    if not updated_time:
        return "DISCONNECTED", "Unknown"

    # Check if status.log is fresh (updated in last 30 seconds)
    now = datetime.now()
    seconds_since_update = (now - updated_time).total_seconds()

    if seconds_since_update > 30:
        # Status log is stale - server likely down
        return "DISCONNECTED", "Unknown"

    # Server is running - get container start time
    container_start = get_container_start_time()

    if container_start:
        uptime = container_start.strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(f"Server uptime based on container start: {uptime}")
        return "CONNECTED", uptime

    # Fallback: unable to get container start time
    logger.warning("Unable to determine container start time, using current time")
    uptime = now.strftime("%Y-%m-%d %H:%M:%S")
    return "CONNECTED", uptime


def get_public_ip():
    """
    Get public IP address using external services.

    Works from Docker container without host network access.
    Uses Python requests library instead of curl.
    """
    # Try ipify.org (HTTPS, reliable)
    try:
        import requests

        response = requests.get("https://api.ipify.org", timeout=10)
        if response.status_code == 200:
            ip = response.text.strip()
            # Basic validation
            if ip and "." in ip:
                return ip
    except Exception as e:
        logger.debug(f"ipify.org failed: {e}")

    # Fallback to icanhazip.com
    try:
        import requests

        response = requests.get("https://icanhazip.com", timeout=10)
        if response.status_code == 200:
            ip = response.text.strip()
            if ip and "." in ip:
                return ip
    except Exception as e:
        logger.debug(f"icanhazip.com failed: {e}")

    return "Unknown"


def get_local_ip():
    """
    Get local IP address.

    Options (in order of priority):
    1. From OPENVPN_LOCAL_IP environment variable
    2. From container's network interface using socket
    3. From container's eth0 interface using ip command (if available)
    4. Unknown
    """
    # Check environment variable first
    env_ip = os.getenv("OPENVPN_LOCAL_IP")
    if env_ip:
        return env_ip

    # Try to get IP using socket (works without external tools)
    try:
        import socket

        # Connect to external IP to determine which interface would be used
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        # Doesn't actually send data, just determines routing
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except Exception as e:
        logger.debug(f"Failed to get IP via socket: {e}")

    # Fallback: try to get from eth0 interface (requires ip command)
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "eth0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "inet " in line:
                    # Extract IP from "inet 172.18.0.2/16 brd ..."
                    ip = line.strip().split()[1].split("/")[0]
                    return ip
    except Exception as e:
        logger.debug(f"Failed to get container IP from eth0: {e}")

    return "Unknown"


def check_ping(ip):
    """
    Check if IP is pingable using socket connection test.

    Since ping requires ICMP and may not be available in container,
    we test TCP connectivity instead (port 80/443).

    Args:
        ip: IP address to check

    Returns:
        "Yes" or "No"
    """
    if ip == "Unknown":
        return "No"

    # Try TCP connection to common ports (more reliable in containers than ICMP ping)
    try:
        import socket

        # Test HTTP/HTTPS ports
        for port in [80, 443]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    return "Yes"
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Socket connectivity test failed: {e}")

    # Fallback to ping command if available
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", ip],
            capture_output=True,
            timeout=5,
        )
        return "Yes" if result.returncode == 0 else "No"
    except Exception:
        pass

    return "No"


def get_geolocation(ip):
    """
    Get geolocation for IP address using ip-api.com.

    WARNING: This reveals the physical location of your server.
    Only enable if absolutely necessary via OPENVPN_SERVER_GEOLOCATION=true.

    Returns:
        dict with city, country, latitude, longitude or None values on failure
    """
    if ip == "Unknown":
        return {"city": None, "country": None, "latitude": None, "longitude": None}

    try:
        import urllib.request

        url = f"http://ip-api.com/json/{ip}"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())

            if data.get("status") == "success":
                return {
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
    except Exception as e:
        logger.warning(f"Failed to get geolocation: {e}")

    return {"city": None, "country": None, "latitude": None, "longitude": None}


def collect_server_status():
    """
    Collect server status information from within Docker container.

    Returns:
        dict with:
        - status: CONNECTED or DISCONNECTED
        - uptime: Server uptime or "Unknown"
        - local_ip: Container/local IP address
        - public_ip: Public IP address
        - pingable: Whether public IP is pingable
        - location: Optional geolocation (only if OPENVPN_SERVER_GEOLOCATION=true)
    """
    logger.info("Collecting server status from container...")

    # Check status and uptime from status.log
    status, uptime = check_server_status()

    # Get IPs
    local_ip = get_local_ip()
    public_ip = get_public_ip()

    # Check if public IP is pingable (more useful than local IP from container)
    pingable = check_ping(public_ip)

    result = {
        "status": status,
        "uptime": uptime,
        "local_ip": local_ip,
        "public_ip": public_ip,
        "pingable": pingable,
    }

    # Optional: Add geolocation if enabled (disabled by default for security)
    geolocation_enabled = os.getenv("OPENVPN_SERVER_GEOLOCATION", "false").lower() == "true"
    if geolocation_enabled:
        logger.info("Server geolocation is enabled - fetching location data...")
        location = get_geolocation(public_ip)
        result["location"] = location
    else:
        logger.debug("Server geolocation is disabled (security best practice)")

    logger.info(f"Server status collected: {status}, Local IP: {local_ip}, Public IP: {public_ip}")

    return result


def save_server_status(data):
    """
    Atomically save server status to JSON file.

    Args:
        data: Server status dict
    """
    output_path = Path(SERVER_STATUS_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    temp_path = output_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        os.replace(temp_path, output_path)
        logger.debug(f"Server status saved to {output_path}")

    except Exception as e:
        logger.error(f"Failed to save server status: {e}")
        if temp_path.exists():
            temp_path.unlink()
        raise


def update_server_status():
    """
    Main function to collect and save server status.

    Call this periodically from logger.py (e.g., every 60 seconds).
    """
    try:
        status_data = collect_server_status()
        save_server_status(status_data)
    except Exception as e:
        logger.exception(f"Error updating server status: {e}")
