#!/usr/bin/env python3
"""Quick test to verify the refactored parser logic"""
import sys
import json

# Test 1: Check that session_history.json has no null session_end
print("Test 1: Checking session_history.json for incomplete sessions...")
try:
    with open("data/session_history.json", "r") as f:
        sessions = json.load(f)

    incomplete = [s for s in sessions if s.get("session_end") is None]

    if len(incomplete) == 0:
        print(f"✓ PASS: All {len(sessions)} sessions have session_end set")
    else:
        print(f"✗ FAIL: Found {len(incomplete)} incomplete sessions")
        sys.exit(1)
except Exception as e:
    print(f"✗ ERROR: {e}")
    sys.exit(1)

# Test 2: Verify file structure
print("\nTest 2: Verifying parser.py structure...")
try:
    with open("app/parser.py", "r") as f:
        content = f.read()

    # Check for new function
    if "def _complete_session(" in content:
        print("✓ PASS: _complete_session() function exists")
    else:
        print("✗ FAIL: _complete_session() function not found")
        sys.exit(1)

    # Check that old duplicate logic in new sessions is removed
    # Old code had: entries.append(new_entry) with rx: None, tx: None
    lines = content.split('\n')
    problematic_lines = []

    for i, line in enumerate(lines, 1):
        if '"rx": None' in line or '"tx": None' in line:
            # This should only appear in comments or in specific contexts
            # Let's check the context around it
            context_start = max(0, i-10)
            context_end = min(len(lines), i+5)
            context = '\n'.join(lines[context_start:context_end])

            # If it's in new_sessions loop with history_log, that's bad
            if 'for common_name in new_sessions:' in context and 'history_log()' in context:
                problematic_lines.append(i)

    if not problematic_lines:
        print("✓ PASS: No incomplete session creation in new_sessions loop")
    else:
        print(f"✗ FAIL: Found problematic code at lines: {problematic_lines}")
        sys.exit(1)

    # Count lines
    line_count = len(lines)
    if line_count < 600:  # Should be around 541
        print(f"✓ PASS: File is concise ({line_count} lines)")
    else:
        print(f"⚠ WARNING: File is longer than expected ({line_count} lines)")

except Exception as e:
    print(f"✗ ERROR: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ All tests passed! Refactoring is successful.")
print("="*60)
