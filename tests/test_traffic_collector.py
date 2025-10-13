import importlib
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def traffic_collector_module(tmp_path, monkeypatch):
    """Setup traffic collector with temp paths."""
    metrics_path = tmp_path / "traffic_metrics.json"

    monkeypatch.setenv("OPENVPN_TRAFFIC_METRICS", str(metrics_path))

    from app import config

    importlib.reload(config)

    from app import traffic_collector

    importlib.reload(traffic_collector)

    return traffic_collector, metrics_path


def test_save_metrics_cleans_up_temp_file_on_error(traffic_collector_module, monkeypatch):
    """Test that temporary files are cleaned up when os.replace() fails."""
    collector, metrics_path = traffic_collector_module

    test_data = {
        "client1": [
            {
                "timestamp": "2024-01-01T12:00:00",
                "bytes_received": 1024,
                "bytes_sent": 2048,
                "speed_rx": 0.5,
                "speed_tx": 1.0,
            }
        ]
    }

    # Mock os.replace to fail
    original_replace = collector.os.replace

    def failing_replace(src, dst):
        # Store the temp file name before it would be replaced
        temp_files = list(metrics_path.parent.glob("tmp*"))
        if temp_files:
            raise OSError("Simulated failure")
        original_replace(src, dst)

    monkeypatch.setattr(collector.os, "replace", failing_replace)

    # Try to save and expect it to fail
    with pytest.raises(OSError, match="Simulated failure"):
        collector.save_metrics(test_data, str(metrics_path))

    # Verify no temporary files are left behind
    temp_files = list(metrics_path.parent.glob("tmp*"))
    assert len(temp_files) == 0, f"Found unexpected temp files: {temp_files}"


def test_save_metrics_success_leaves_no_temp_files(traffic_collector_module):
    """Test that successful save operations don't leave temp files."""
    collector, metrics_path = traffic_collector_module

    test_data = {
        "client1": [
            {
                "timestamp": "2024-01-01T12:00:00",
                "bytes_received": 1024,
                "bytes_sent": 2048,
                "speed_rx": 0.5,
                "speed_tx": 1.0,
            }
        ]
    }

    # Save successfully
    collector.save_metrics(test_data, str(metrics_path))

    # Verify no temporary files are left behind
    temp_files = list(metrics_path.parent.glob("tmp*"))
    assert len(temp_files) == 0, f"Found unexpected temp files: {temp_files}"

    # Verify the data was saved correctly
    with metrics_path.open() as f:
        saved_data = json.load(f)
    assert saved_data == test_data


def test_save_metrics_handles_write_error_during_json_dump(traffic_collector_module, monkeypatch):
    """Test cleanup when json.dump fails."""
    collector, metrics_path = traffic_collector_module

    test_data = {"client1": [{"timestamp": "2024-01-01T12:00:00"}]}

    # Mock json.dump to fail
    original_dump = collector.json.dump

    def failing_dump(obj, fp, **kwargs):
        raise ValueError("Simulated JSON error")

    monkeypatch.setattr(collector.json, "dump", failing_dump)

    # Try to save and expect it to fail
    with pytest.raises(ValueError, match="Simulated JSON error"):
        collector.save_metrics(test_data, str(metrics_path))

    # Verify no temporary files are left behind
    temp_files = list(metrics_path.parent.glob("tmp*"))
    assert len(temp_files) == 0, f"Found unexpected temp files: {temp_files}"
