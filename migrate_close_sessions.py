#!/usr/bin/env python3
"""
Migration script to close incomplete sessions in session_history.json
Sets session_end to 23:59:59 of the same day as the session start.
"""
import json
import sys
from datetime import datetime

HISTORY_FILE = "data/session_history.json"


def close_incomplete_sessions():
    """Close all sessions with session_end: null"""

    print(f"Reading {HISTORY_FILE}...")

    try:
        with open(HISTORY_FILE, "r") as f:
            sessions = json.load(f)
    except FileNotFoundError:
        print(f"Error: {HISTORY_FILE} not found!")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {HISTORY_FILE}: {e}")
        return 1

    if not isinstance(sessions, list):
        print(f"Error: Expected list in {HISTORY_FILE}, got {type(sessions)}")
        return 1

    print(f"Total sessions: {len(sessions)}")

    # Find incomplete sessions
    incomplete_count = 0
    closed_count = 0

    for session in sessions:
        if session.get("session_end") is None:
            incomplete_count += 1
            timestamp = session.get("timestamp")

            if not timestamp:
                print(f"Warning: Session {session.get('session_id')} has no timestamp, skipping")
                continue

            try:
                # Parse the timestamp
                session_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

                # Set session_end to 23:59:59 of the same day
                session_end = session_date.replace(hour=23, minute=59, second=59)
                session["session_end"] = session_end.strftime("%Y-%m-%d %H:%M:%S")

                closed_count += 1

                print(
                    f"Closed session: {session.get('name')} ({timestamp} -> {session['session_end']})"
                )

            except ValueError as e:
                print(
                    f"Warning: Invalid timestamp format for session {session.get('session_id')}: {e}"
                )
                continue

    print(f"\nFound {incomplete_count} incomplete sessions")
    print(f"Successfully closed {closed_count} sessions")

    if closed_count > 0:
        # Backup original file
        backup_file = f"{HISTORY_FILE}.backup"
        print(f"\nCreating backup: {backup_file}")

        with open(backup_file, "w") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

        # Save updated file
        print(f"Saving updated {HISTORY_FILE}...")

        with open(HISTORY_FILE, "w") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
            f.write("\n")

        print(f"✓ Migration completed successfully!")
        print(f"  - Backup saved to: {backup_file}")
        print(f"  - {closed_count} sessions closed")
    else:
        print("\nNo sessions to close, nothing changed.")

    return 0


if __name__ == "__main__":
    sys.exit(close_incomplete_sessions())
