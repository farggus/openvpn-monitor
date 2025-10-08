# logger.py
import time
from app.parser import parse_status_log
from app.traffic_collector import collect_traffic_metrics

if __name__ == "__main__":
    print("OpenVPN background logger started...")
    while True:
        # Parse status log and get client data
        clients = parse_status_log()

        # Collect traffic metrics for charts
        collect_traffic_metrics(clients)

        time.sleep(10)
