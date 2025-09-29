#!/bin/bash

pid=$(pgrep -f openvpn | head -n1)
if [ -z "$pid" ]; then
  status="DISCONNECTED"
  uptime="Unknown"
else
  status="CONNECTED"
  start_time=$(date -d "@$(stat -c %Y /proc/$pid)" +"%Y-%m-%d %H:%M:%S")
  uptime="$start_time"
fi

# определяем IP
ip=$(ip -4 addr show tun0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

# устойчивое определение публичного IP
public_ip=$(dig +short myip.opendns.com @resolver1.opendns.com)
if [ -z "$public_ip" ]; then
  public_ip=$(curl -s https://api.ipify.org)
fi

pingable="No"
ping -c1 -W1 "$ip" >/dev/null 2>&1 && pingable="Yes"

echo '{
  "status": "'$status'",
  "uptime": "'$uptime'",
  "local_ip": "'$ip'",
  "public_ip": "'$public_ip'",
  "pingable": "'$pingable'"
}' > /var/log/openvpn/server_status.json
