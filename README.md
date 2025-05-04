# OpenVPN Monitor

**OpenVPN Monitor** is a lightweight Flask-based web dashboard for monitoring OpenVPN clients and server statistics.

## Features

- Real-time client monitoring
- Live traffic graph (Rx/Tx per client)
- IP geolocation with map (Leaflet + ipapi)
- Session history with filters
- Mobile-friendly UI
- Dockerized for easy deployment
- Server status overview (mode, uptime, traffic summary)

## Quick Start

```bash
git clone https://github.com/your-username/openvpn-monitor.git
cd openvpn-monitor
docker-compose up --build -d
```
Make sure to mount your OpenVPN log directory (/var/log/openvpn) as a volume in Docker.

File Structure
app/ – Flask backend

templates/index.html – Frontend UI

parser.py – OpenVPN log parser

logger.py – Background parser loop

supervisord.conf – Process manager for app and logger

docker-compose.yml – Deployment configuration

API Endpoints
/api/clients – Live client list

/api/server-status – Server status info

/api/history – Session history

License
Private project for internal use.

Author
Developed by Farggus
