# logger.py
import time
from app.parser import parse_status_log

if __name__ == "__main__":
    print("OpenVPN background logger started...")
    while True:
        parse_status_log()
        time.sleep(10)
