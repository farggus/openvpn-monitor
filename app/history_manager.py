# history_manager.py
"""
History rotation and archival manager.

This module handles automatic rotation of session_history.json to prevent
unlimited growth. Old entries are compressed and archived by month.
"""

from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from .config import HISTORY_LOG_PATH
from .parser import history_log

logger = logging.getLogger(__name__)

# Configuration
MAX_HISTORY_DAYS = 90  # Keep last 90 days in main file
ARCHIVE_DIR = Path("data/history_archive")


def rotate_history_if_needed() -> None:
    """
    Rotate history file if it contains entries older than MAX_HISTORY_DAYS.

    Process:
    1. Load all entries from session_history.json
    2. Split into recent (keep in main file) and old (archive)
    3. Group old entries by month (YYYY-MM)
    4. Compress and save each month to separate .json.gz file
    5. Update main file with only recent entries

    Archives are stored in: data/history_archive/session_history_YYYY-MM.json.gz

    This function is idempotent - safe to call multiple times.
    """
    try:
        # Ensure archive directory exists
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=MAX_HISTORY_DAYS)).strftime("%Y-%m-%d")

        # Load all entries using the existing context manager (with file locking)
        with history_log() as entries:
            if not entries:
                logger.debug("History file is empty, nothing to rotate")
                return

            # Split entries into old and recent
            old_entries = [e for e in entries if e.get("timestamp", "9999-99-99") < cutoff_date]
            recent_entries = [e for e in entries if e.get("timestamp", "0000-00-00") >= cutoff_date]

            if not old_entries:
                logger.debug(f"No entries older than {MAX_HISTORY_DAYS} days, rotation not needed")
                return

            logger.info(
                f"Starting rotation: {len(old_entries)} old entries, "
                f"{len(recent_entries)} recent entries"
            )

            # Group old entries by month
            by_month: Dict[str, List[Dict[str, Any]]] = {}
            for entry in old_entries:
                timestamp = entry.get("timestamp", "")
                if len(timestamp) >= 7:  # YYYY-MM-DD format
                    month = timestamp[:7]  # Extract YYYY-MM
                    by_month.setdefault(month, []).append(entry)

            # Archive each month
            archived_count = 0
            for month, month_entries in sorted(by_month.items()):
                archive_file = ARCHIVE_DIR / f"session_history_{month}.json.gz"

                try:
                    # Load existing archive if it exists
                    existing = []
                    if archive_file.exists():
                        with gzip.open(archive_file, "rt", encoding="utf-8") as f:
                            try:
                                existing = json.load(f)
                            except json.JSONDecodeError:
                                logger.warning(f"Corrupted archive {archive_file}, will recreate")
                                existing = []

                    # Merge with new entries (avoid duplicates by session_id)
                    existing_ids = {e.get("session_id") for e in existing}
                    new_entries = [
                        e for e in month_entries if e.get("session_id") not in existing_ids
                    ]

                    if new_entries:
                        combined = existing + new_entries
                        # Sort by timestamp
                        combined.sort(key=lambda e: e.get("timestamp", ""))

                        # Write compressed archive
                        with gzip.open(archive_file, "wt", encoding="utf-8") as f:
                            json.dump(combined, f, indent=2, ensure_ascii=False)

                        archived_count += len(new_entries)
                        logger.info(
                            f"Archived {len(new_entries)} entries to {archive_file.name} "
                            f"(total: {len(combined)})"
                        )

                except Exception as e:
                    logger.exception(f"Failed to archive month {month}: {e}")
                    # Continue with other months even if one fails

            # Update main file with only recent entries (in-place modification)
            # The history_log context manager will handle atomic write
            entries[:] = recent_entries

            logger.info(
                f"Rotation completed: archived {archived_count} entries, "
                f"kept {len(recent_entries)} recent entries"
            )

            # Log file size reduction
            try:
                if Path(HISTORY_LOG_PATH).exists():
                    new_size = Path(HISTORY_LOG_PATH).stat().st_size / (1024 * 1024)
                    logger.info(f"New history file size: {new_size:.2f} MB")
            except Exception:
                pass

    except Exception as e:
        logger.exception(f"Failed to rotate history: {e}")
        # Don't raise - rotation failure shouldn't crash the logger


def get_archive_stats() -> Dict[str, Any]:
    """
    Get statistics about archived data.

    Returns:
        dict: Archive statistics including file count, total entries, size
    """
    stats = {
        "archive_dir": str(ARCHIVE_DIR),
        "archive_files": [],
        "total_archived_entries": 0,
        "total_archive_size_mb": 0.0,
    }

    try:
        if not ARCHIVE_DIR.exists():
            return stats

        for archive_file in sorted(ARCHIVE_DIR.glob("session_history_*.json.gz")):
            try:
                # Read compressed file
                with gzip.open(archive_file, "rt", encoding="utf-8") as f:
                    entries = json.load(f)

                file_size = archive_file.stat().st_size / (1024 * 1024)

                stats["archive_files"].append(
                    {
                        "file": archive_file.name,
                        "month": archive_file.stem.replace("session_history_", ""),
                        "entries": len(entries),
                        "size_mb": round(file_size, 3),
                    }
                )

                stats["total_archived_entries"] += len(entries)
                stats["total_archive_size_mb"] += file_size

            except Exception as e:
                logger.warning(f"Failed to read archive {archive_file.name}: {e}")

        stats["total_archive_size_mb"] = round(stats["total_archive_size_mb"], 3)

    except Exception as e:
        logger.exception(f"Failed to get archive stats: {e}")

    return stats


def load_month_from_archive(year_month: str) -> List[Dict[str, Any]]:
    """
    Load archived entries for a specific month.

    Args:
        year_month: Month in YYYY-MM format (e.g., "2025-10")

    Returns:
        List of session entries for that month

    Example:
        >>> entries = load_month_from_archive("2025-09")
        >>> print(f"Found {len(entries)} sessions in September 2025")
    """
    archive_file = ARCHIVE_DIR / f"session_history_{year_month}.json.gz"

    if not archive_file.exists():
        logger.warning(f"Archive for {year_month} not found: {archive_file}")
        return []

    try:
        with gzip.open(archive_file, "rt", encoding="utf-8") as f:
            entries = json.load(f)
        logger.info(f"Loaded {len(entries)} entries from archive {year_month}")
        return entries
    except Exception as e:
        logger.exception(f"Failed to load archive {year_month}: {e}")
        return []
