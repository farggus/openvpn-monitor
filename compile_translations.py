#!/usr/bin/env python3
"""
Compile .po files to .mo files for Flask-Babel
This script uses the babel library to compile translations
"""
import os
import sys
from pathlib import Path

def compile_translations():
    """Compile all .po files to .mo files in the translations directory"""
    translations_dir = Path(__file__).parent / "translations"

    if not translations_dir.exists():
        print(f"Error: Translations directory not found: {translations_dir}")
        sys.exit(1)

    # Find all .po files
    po_files = list(translations_dir.glob("*/LC_MESSAGES/*.po"))

    if not po_files:
        print("No .po files found to compile")
        return

    print(f"Found {len(po_files)} .po file(s) to compile")

    try:
        from babel.messages.mofile import write_mo
        from babel.messages.pofile import read_po
    except ImportError:
        print("Error: Babel is not installed. Install it with: pip install Babel")
        sys.exit(1)

    for po_file in po_files:
        mo_file = po_file.with_suffix(".mo")
        print(f"Compiling {po_file.relative_to(translations_dir)} -> {mo_file.name}")

        try:
            with open(po_file, 'rb') as f:
                catalog = read_po(f)

            with open(mo_file, 'wb') as f:
                write_mo(f, catalog)

            print(f"  ✓ Successfully compiled to {mo_file.relative_to(translations_dir)}")
        except Exception as e:
            print(f"  ✗ Error compiling {po_file}: {e}")
            sys.exit(1)

    print(f"\nSuccessfully compiled {len(po_files)} translation file(s)")

if __name__ == "__main__":
    compile_translations()
