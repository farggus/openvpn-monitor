"""
Traffic metrics collector for historical chart data.

Collects and stores traffic speed metrics for all connected clients.
Maintains up to 24 hours of historical data with 10-second intervals.
"""

import datetime
import json
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import Dict, List, Optional

import fcntl

from .config import TRAFFIC_METRICS_PATH, LOCAL_TZ

logger = logging.getLogger(__name__)

# Maximum age of metrics to keep (24 hours)
MAX_METRIC_AGE_SECONDS = 24 * 60 * 60


@contextmanager
def metrics_lock(path: str = TRAFFIC_METRICS_PATH):
    """Prevent concurrent modifications of the metrics file."""
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


def load_metrics(path: str = TRAFFIC_METRICS_PATH) -> Dict[str, List[Dict]]:
    """
    Load traffic metrics from JSON file.

    Returns:
        Dict mapping client names to list of metric points
    """
    target_path = os.path.abspath(path)

    if not os.path.exists(target_path):
        return {}

    try:
        with open(target_path, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load metrics: {e}")
        return {}


def save_metrics(metrics: Dict[str, List[Dict]], path: str = TRAFFIC_METRICS_PATH):
    """
    Save traffic metrics to JSON file atomically.

    Args:
        metrics: Dict mapping client names to list of metric points
        path: Path to metrics file
    """
    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    tmp_file_name = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=directory, delete=False) as tmp_file:
            tmp_file_name = tmp_file.name
            json.dump(metrics, tmp_file, ensure_ascii=False, indent=2)
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


def cleanup_old_metrics(
    metrics: Dict[str, List[Dict]], now: datetime.datetime
) -> Dict[str, List[Dict]]:
    """
    Remove metric points older than 24 hours.

    Args:
        metrics: Current metrics data
        now: Current timestamp

    Returns:
        Cleaned metrics dict
    """
    cutoff_time = now - datetime.timedelta(seconds=MAX_METRIC_AGE_SECONDS)
    cutoff_str = cutoff_time.isoformat()

    cleaned = {}
    for client_name, points in metrics.items():
        if not isinstance(points, list):
            continue

        # Keep only recent points
        recent_points = [
            p for p in points if isinstance(p, dict) and p.get("timestamp", "") >= cutoff_str
        ]

        if recent_points:
            cleaned[client_name] = recent_points

    return cleaned


def calculate_speed(current_bytes: int, previous_bytes: int, time_delta: float) -> float:
    """
    Calculate speed in MB/s.

    Args:
        current_bytes: Current byte count
        previous_bytes: Previous byte count
        time_delta: Time difference in seconds

    Returns:
        Speed in MB/s
    """
    if time_delta <= 0:
        return 0.0

    bytes_diff = max(0, current_bytes - previous_bytes)
    mb_per_second = (bytes_diff / (1024 * 1024)) / time_delta

    return round(mb_per_second, 6)


def collect_traffic_metrics(clients_data: List[Dict]):
    """
    Collect current traffic metrics from clients data and update metrics file.

    Args:
        clients_data: List of client records from parse_status_log()
    """
    if not clients_data:
        return

    now = datetime.datetime.now(LOCAL_TZ)
    timestamp = now.isoformat()

    with metrics_lock():
        # Load existing metrics
        metrics = load_metrics()

        # Create a dict for quick lookup of previous values
        previous_values = {}
        for client_name, points in metrics.items():
            if points:
                last_point = points[-1]
                previous_values[client_name] = {
                    "timestamp": last_point.get("timestamp"),
                    "bytes_received": last_point.get("bytes_received", 0),
                    "bytes_sent": last_point.get("bytes_sent", 0),
                }

        # Process each client
        for client in clients_data:
            common_name = client.get("common_name")
            if not common_name:
                continue

            bytes_received = client.get("bytes_received", 0)
            bytes_sent = client.get("bytes_sent", 0)

            # Calculate speeds
            speed_rx = 0.0
            speed_tx = 0.0

            if common_name in previous_values:
                prev = previous_values[common_name]
                prev_timestamp = prev.get("timestamp")

                if prev_timestamp:
                    try:
                        prev_dt = datetime.datetime.fromisoformat(prev_timestamp)
                        time_delta = (now - prev_dt).total_seconds()

                        speed_rx = calculate_speed(
                            bytes_received, prev["bytes_received"], time_delta
                        )
                        speed_tx = calculate_speed(bytes_sent, prev["bytes_sent"], time_delta)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to calculate speed for {common_name}: {e}")

            # Create new metric point
            metric_point = {
                "timestamp": timestamp,
                "bytes_received": bytes_received,
                "bytes_sent": bytes_sent,
                "speed_rx": speed_rx,
                "speed_tx": speed_tx,
            }

            # Add to metrics
            if common_name not in metrics:
                metrics[common_name] = []

            metrics[common_name].append(metric_point)

        # Cleanup old metrics
        metrics = cleanup_old_metrics(metrics, now)

        # Save updated metrics
        save_metrics(metrics)


def get_metrics_for_period(
    client_name: Optional[str] = None, minutes: int = 30, path: str = TRAFFIC_METRICS_PATH
) -> Dict[str, List[Dict]]:
    """
    Get traffic metrics for a specific time period.

    Args:
        client_name: Specific client name, or None for all clients
        minutes: Number of minutes to look back
        path: Path to metrics file

    Returns:
        Dict mapping client names to filtered metric points
    """
    now = datetime.datetime.now(LOCAL_TZ)
    cutoff_time = now - datetime.timedelta(minutes=minutes)
    cutoff_str = cutoff_time.isoformat()

    with metrics_lock(path):
        all_metrics = load_metrics(path)

    filtered = {}

    # If specific client requested
    if client_name:
        if client_name in all_metrics:
            points = all_metrics[client_name]
            filtered_points = [
                p for p in points if isinstance(p, dict) and p.get("timestamp", "") >= cutoff_str
            ]
            if filtered_points:
                filtered[client_name] = filtered_points
    else:
        # Return all clients
        for name, points in all_metrics.items():
            filtered_points = [
                p for p in points if isinstance(p, dict) and p.get("timestamp", "") >= cutoff_str
            ]
            if filtered_points:
                filtered[name] = filtered_points

    return filtered
