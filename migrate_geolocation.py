#!/usr/bin/env python3
"""
Migration script to enrich session_history.json with geolocation data from client_geolocation.json
"""
import json
import sys
from pathlib import Path

def load_json(filepath):
    """Load JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)

def save_json(filepath, data):
    """Save JSON file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {filepath}")
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        sys.exit(1)

def build_ip_to_location_map(geo_data):
    """Build a mapping from IP address to location data"""
    ip_map = {}

    clients = geo_data.get('clients', {})
    for client_name, client_data in clients.items():
        ips = client_data.get('ips', {})
        for ip, ip_data in ips.items():
            location = ip_data.get('location')
            if location:
                ip_map[ip] = {
                    'city': location.get('city'),
                    'country': location.get('country'),
                    'latitude': location.get('latitude'),
                    'longitude': location.get('longitude')
                }

    return ip_map

def migrate_session_history(history_file, geo_file):
    """Migrate session history with geolocation data"""

    print("Loading geolocation database...")
    geo_data = load_json(geo_file)

    print("Building IP to location mapping...")
    ip_to_location = build_ip_to_location_map(geo_data)
    print(f"Found {len(ip_to_location)} unique IP addresses with location data")

    print("\nLoading session history...")
    sessions = load_json(history_file)
    print(f"Found {len(sessions)} session records")

    # Statistics
    updated = 0
    already_has_location = 0
    no_location_found = 0

    print("\nEnriching sessions with geolocation data...")
    for session in sessions:
        ip = session.get('ip')

        # Skip if already has location
        if 'location' in session and session['location']:
            already_has_location += 1
            continue

        # Find location for this IP
        if ip and ip in ip_to_location:
            session['location'] = ip_to_location[ip]
            updated += 1
        else:
            # Add null location if not found
            session['location'] = {
                'city': None,
                'country': None,
                'latitude': None,
                'longitude': None
            }
            no_location_found += 1

    print(f"\n=== Migration Summary ===")
    print(f"Total sessions: {len(sessions)}")
    print(f"Updated with location: {updated}")
    print(f"Already had location: {already_has_location}")
    print(f"No location found: {no_location_found}")

    # Save updated history
    print(f"\nSaving updated session history...")
    save_json(history_file, sessions)

    print("\n✓ Migration completed successfully!")

if __name__ == '__main__':
    # File paths
    data_dir = Path('/home/app_data/docker/openvpn-monitor/data')
    history_file = data_dir / 'session_history.json'
    geo_file = data_dir / 'client_geolocation.json'

    # Check files exist
    if not history_file.exists():
        print(f"Error: {history_file} not found")
        sys.exit(1)

    if not geo_file.exists():
        print(f"Error: {geo_file} not found")
        sys.exit(1)

    print("=== Session History Geolocation Migration ===\n")
    migrate_session_history(history_file, geo_file)
