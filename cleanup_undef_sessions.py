#!/usr/bin/env python3
"""
Cleanup script to remove UNDEF sessions with Rx/Tx < 1 MB from session history.
"""
import json
import fcntl
import os


def cleanup_undef_sessions(history_path="data/session_history.json"):
    """Remove UNDEF sessions where both rx and tx are < 1 MB"""
    target_path = os.path.abspath(history_path)

    if not os.path.exists(target_path):
        print(f"History file not found: {target_path}")
        return

    print(f"Processing: {target_path}")

    # Use file locking to prevent race conditions
    with open(target_path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            # Load existing history
            f.seek(0)
            try:
                sessions = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading JSON: {e}")
                return

            if not isinstance(sessions, list):
                print("Invalid session history format")
                return

            original_count = len(sessions)
            print(f"Original session count: {original_count}")

            # Filter out UNDEF sessions with Rx/Tx < 1 MB
            filtered_sessions = []
            removed_count = 0

            for session in sessions:
                name = session.get("name", "")
                rx = session.get("rx")
                tx = session.get("tx")

                # Keep session if:
                # 1. Not UNDEF, OR
                # 2. rx >= 1 MB, OR
                # 3. tx >= 1 MB
                if name != "UNDEF":
                    filtered_sessions.append(session)
                else:
                    # Convert None to 0 for comparison
                    rx_val = rx if rx is not None else 0
                    tx_val = tx if tx is not None else 0

                    # Keep if either rx or tx >= 1 MB
                    if rx_val >= 1.0 or tx_val >= 1.0:
                        filtered_sessions.append(session)
                    else:
                        removed_count += 1

            print(f"Removed {removed_count} UNDEF sessions with Rx/Tx < 1 MB")
            print(f"Remaining sessions: {len(filtered_sessions)}")

            # Write back the cleaned data
            f.seek(0)
            f.truncate()
            json.dump(filtered_sessions, f, indent=2)

        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

    print("Cleanup completed successfully!")


if __name__ == "__main__":
    cleanup_undef_sessions()
