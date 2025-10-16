# Adding Basic Authentication to Standalone Deployment

If you deployed with `docker-compose.standalone.yml`, the application is accessible without authentication. For production use, add nginx as a reverse proxy with Basic Auth.

## Prerequisites

- OpenVPN Monitor running in standalone mode (port 5000)
- Root or sudo access to install nginx

## Installation

### Step 1: Install nginx and htpasswd

```bash
sudo apt update
sudo apt install nginx apache2-utils
```

### Step 2: Create Password File

```bash
# Create password file with username 'openvpn'
sudo htpasswd -c /etc/nginx/.htpasswd openvpn

# You will be prompted to enter and confirm password
```

**For additional users:**
```bash
# Add more users (without -c flag to append)
sudo htpasswd /etc/nginx/.htpasswd username2
```

### Step 3: Create nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/openvpn-monitor
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-server-ip-or-domain;

    # Basic Authentication
    auth_basic "OpenVPN Monitor";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 4: Enable Site and Test

```bash
# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/openvpn-monitor /etc/nginx/sites-enabled/

# Test nginx configuration for syntax errors
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx

# Check nginx status
sudo systemctl status nginx
```

### Step 5: Access Application

Now access the application at:
- `http://your-server-ip` (port 80)
- `http://your-domain.com` (if using domain name)

You will be prompted for username and password.

## Optional: Add HTTPS with Let's Encrypt

### Prerequisites
- Domain name pointing to your server
- Ports 80 and 443 open in firewall

### Installation

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d vpn-monitor.example.com

# Follow interactive prompts:
# - Enter email for urgent renewal notices
# - Agree to terms of service
# - Choose whether to redirect HTTP to HTTPS (recommended: yes)
```

Certbot will automatically:
- Obtain SSL certificate from Let's Encrypt
- Modify nginx configuration to use HTTPS
- Set up automatic renewal (via systemd timer)

### Verify Auto-Renewal

```bash
# Test renewal process (dry run)
sudo certbot renew --dry-run

# Check renewal timer status
sudo systemctl status certbot.timer
```

Certificates are automatically renewed before expiration (every 60 days).

## Manual Configuration with Self-Signed Certificate

If you don't have a domain or prefer self-signed certificates:

```bash
# Generate self-signed certificate (valid 365 days)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/openvpn-monitor.key \
  -out /etc/ssl/certs/openvpn-monitor.crt

# Update nginx configuration
sudo nano /etc/nginx/sites-available/openvpn-monitor
```

Add HTTPS server block:

```nginx
server {
    listen 443 ssl;
    server_name your-server-ip-or-domain;

    ssl_certificate /etc/ssl/certs/openvpn-monitor.crt;
    ssl_certificate_key /etc/ssl/private/openvpn-monitor.key;

    # Basic Authentication
    auth_basic "OpenVPN Monitor";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-server-ip-or-domain;
    return 301 https://$server_name$request_uri;
}
```

Test and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Note:** Browsers will show a security warning for self-signed certificates. You can safely proceed by adding a security exception.

## Troubleshooting

### nginx Won't Start

```bash
# Check for syntax errors
sudo nginx -t

# View detailed error logs
sudo journalctl -u nginx -n 50

# Check if port 80 is already in use
sudo netstat -tlnp | grep :80
```

### Authentication Not Working

```bash
# Verify password file exists and has correct permissions
sudo ls -l /etc/nginx/.htpasswd

# Test password file
sudo htpasswd -v /etc/nginx/.htpasswd openvpn

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

### 502 Bad Gateway Error

This means nginx can't connect to the application:

```bash
# Verify OpenVPN Monitor is running on port 5000
docker compose -f docker-compose.standalone.yml ps

# Check if port 5000 is listening
sudo netstat -tlnp | grep :5000

# Test direct connection
curl http://localhost:5000
```

### Certificate Renewal Failed

```bash
# Check certbot logs
sudo journalctl -u certbot -n 50

# Manually renew certificate
sudo certbot renew --force-renewal

# Verify nginx configuration after renewal
sudo nginx -t
sudo systemctl reload nginx
```

## Alternative: Apache as Reverse Proxy

If you prefer Apache over nginx:

### Install Apache

```bash
sudo apt install apache2 apache2-utils
```

### Enable Required Modules

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod ssl
sudo a2enmod headers
```

### Create Configuration

```bash
sudo nano /etc/apache2/sites-available/openvpn-monitor.conf
```

Add this configuration:

```apache
<VirtualHost *:80>
    ServerName your-domain.com

    # Basic Authentication
    <Location />
        AuthType Basic
        AuthName "OpenVPN Monitor"
        AuthUserFile /etc/apache2/.htpasswd
        Require valid-user
    </Location>

    # Reverse Proxy
    ProxyPreserveHost On
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/openvpn-monitor-error.log
    CustomLog ${APACHE_LOG_DIR}/openvpn-monitor-access.log combined
</VirtualHost>
```

### Create Password File

```bash
sudo htpasswd -c /etc/apache2/.htpasswd openvpn
```

### Enable Site

```bash
sudo a2ensite openvpn-monitor
sudo systemctl reload apache2
```

### HTTPS with Let's Encrypt (Apache)

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d vpn-monitor.example.com
```

## Security Best Practices

1. **Strong Passwords:** Use long, random passwords for Basic Auth
2. **Always Use HTTPS:** Never expose passwords over unencrypted HTTP
3. **Firewall Rules:** Restrict access to known IP addresses if possible
4. **Regular Updates:** Keep nginx/Apache and SSL certificates updated
5. **Monitor Access Logs:** Check for suspicious login attempts

```bash
# Monitor nginx access logs
sudo tail -f /var/log/nginx/access.log

# Monitor failed authentication attempts
sudo grep "401" /var/log/nginx/access.log
```
