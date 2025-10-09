"""View counter tracking module."""

import fcntl
import json
import logging
import os
from pathlib import Path

from .config import VIEW_COUNTER_PATH

logger = logging.getLogger(__name__)


def increment_view_counter() -> int:
    """Increment the view counter and return the new value."""
    lock_path = VIEW_COUNTER_PATH + ".lock"
    Path(lock_path).touch(exist_ok=True)

    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        try:
            if os.path.exists(VIEW_COUNTER_PATH):
                with open(VIEW_COUNTER_PATH, "r") as f:
                    data = json.load(f)
            else:
                data = {"count": 0}

            data["count"] = data.get("count", 0) + 1

            temp_path = VIEW_COUNTER_PATH + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)

            os.replace(temp_path, VIEW_COUNTER_PATH)

            return data["count"]

        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def get_view_counter() -> int:
    """Get the current view counter value."""
    try:
        if os.path.exists(VIEW_COUNTER_PATH):
            with open(VIEW_COUNTER_PATH, "r") as f:
                data = json.load(f)
            return data.get("count", 0)
        else:
            return 0
    except (OSError, json.JSONDecodeError) as e:
        logger.exception(f"Failed to read view counter: {e}")
        return 0
