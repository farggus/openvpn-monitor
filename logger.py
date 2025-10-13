# logger.py
import json
import logging
import sys
import time
from datetime import datetime
from app.parser import parse_status_log
from app.traffic_collector import collect_traffic_metrics, cleanup_old_traffic_metrics

# Configure logging to stdout for Docker container
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("OpenVPN background logger started...")

    error_count = 0
    max_consecutive_errors = 10
    last_cleanup = datetime.now()
    CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour
    COLLECTION_INTERVAL = 10  # seconds

    while True:
        start_time = datetime.now()

        try:
            # Parse status log and get client data (returns tuple now)
            clients, _ = parse_status_log()

            # Collect traffic metrics for charts
            collect_traffic_metrics(clients)

            # Cleanup old metrics once per hour
            now = datetime.now()
            if (now - last_cleanup).total_seconds() >= CLEANUP_INTERVAL_SECONDS:
                logger.info("Running metrics cleanup...")
                cleanup_old_traffic_metrics()
                last_cleanup = now

            # Reset error counter on successful iteration
            error_count = 0

        except FileNotFoundError as e:
            logger.error(f"Status log file not found: {e}")
            error_count += 1

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data: {e}")
            error_count += 1

        except Exception as e:
            logger.exception(f"Unexpected error in background loop: {e}")
            error_count += 1

        # Emergency exit if too many consecutive errors
        if error_count >= max_consecutive_errors:
            logger.critical(f"Too many consecutive errors ({error_count}), exiting")
            sys.exit(1)

        # Sleep with compensation for execution time
        elapsed = (datetime.now() - start_time).total_seconds()
        sleep_time = max(0, COLLECTION_INTERVAL - elapsed)

        if sleep_time == 0:
            logger.warning(
                f"Collection took {elapsed:.2f}s, longer than interval {COLLECTION_INTERVAL}s"
            )

        time.sleep(sleep_time)
