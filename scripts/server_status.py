#!/usr/bin/env python3
"""
Server status collection script for OpenVPN Monitor.
Safely creates JSON with server status information.

Replaces server_status.sh with secure implementation:
- Uses json.dump() for safe JSON creation
- Atomic file writes
- Reads output path from environment variable
- No server geolocation (security improvement)
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_openvpn_pid():
    """Get OpenVPN process PID."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "openvpn"], capture_output=True, text=True, check=True, timeout=5
        )
        pids = result.stdout.strip().split("\n")
        return pids[0] if pids and pids[0] else None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def get_process_start_time(pid):
    """Get process start time from /proc filesystem."""
    try:
        proc_path = Path(f"/proc/{pid}")
        if proc_path.exists():
            stat_result = proc_path.stat()
            start_time = datetime.fromtimestamp(stat_result.st_mtime)
            return start_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.warning(f"Failed to get process start time: {e}")
    return "Unknown"


def get_local_ip():
    """Get local IP address (tun0 or eth0)."""
    # Try tun0 first (VPN interface)
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "tun0"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "inet " in line:
                    ip = line.strip().split()[1].split("/")[0]
                    return ip
    except Exception as e:
        logger.debug(f"tun0 not available: {e}")

    # Fallback to eth0
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "eth0"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "inet " in line:
                    ip = line.strip().split()[1].split("/")[0]
                    return ip
    except Exception as e:
        logger.warning(f"Failed to get local IP: {e}")

    return "Unknown"


def get_public_ip():
    """Get public IP address using external services."""
    # Try OpenDNS resolver first
    try:
        result = subprocess.run(
            ["dig", "+short", "myip.opendns.com", "@resolver1.opendns.com"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"dig failed: {e}")

    # Fallback to ipify.org
    try:
        result = subprocess.run(
            ["curl", "-s", "https://api.ipify.org"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Failed to get public IP: {e}")

    return "Unknown"


def check_ping(ip):
    """Check if IP is pingable."""
    if ip == "Unknown":
        return "No"

    try:
        result = subprocess.run(["ping", "-c1", "-W1", ip], capture_output=True, timeout=5)
        return "Yes" if result.returncode == 0 else "No"
    except Exception:
        return "No"


def get_server_status():
    """
    Collect server status information.

    Returns dict with:
    - status: CONNECTED or DISCONNECTED
    - uptime: Process start time or "Unknown"
    - local_ip: Local IP address
    - public_ip: Public IP address
    - pingable: Whether local IP is pingable
    """
    pid = get_openvpn_pid()

    if pid:
        status = "CONNECTED"
        uptime = get_process_start_time(pid)
    else:
        status = "DISCONNECTED"
        uptime = "Unknown"

    local_ip = get_local_ip()
    public_ip = get_public_ip()
    pingable = check_ping(local_ip)

    return {
        "status": status,
        "uptime": uptime,
        "local_ip": local_ip,
        "public_ip": public_ip,
        "pingable": pingable,
    }


def atomic_write_json(data, output_path):
    """
    Atomically write JSON data to file.

    Uses temporary file + os.replace() to ensure atomic write.
    """
    output_path = Path(output_path)
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
        logger.info(f"Successfully wrote server status to {output_path}")

    except Exception as e:
        logger.error(f"Failed to write server status: {e}")
        if temp_path.exists():
            temp_path.unlink()
        raise


def main():
    """Main entry point."""
    # Get output path from environment variable
    output_file = os.getenv("OPENVPN_SERVER_STATUS", "/app/data/server_status.json")

    try:
        logger.info("Collecting server status...")
        status_data = get_server_status()

        logger.info(
            f"Status: {status_data['status']}, "
            f"Local IP: {status_data['local_ip']}, "
            f"Public IP: {status_data['public_ip']}"
        )

        atomic_write_json(status_data, output_file)

    except Exception as e:
        logger.exception(f"Error collecting server status: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
