# Deployment Guide

## Deploying with Reverse Proxy

To deploy this application with a reverse proxy on your personal website, follow these steps:

### 1. Production Flask Setup

Update `web_frontend.py` for production:

- Change `debug=True` to `debug=False`
- Change `host="0.0.0.0"` to `host="127.0.0.1"` for security
- Consider using a WSGI server like gunicorn

### 2. Install Production Server

```bash
pip install gunicorn
```

Create `wsgi.py`:

```python
#!/usr/bin/env python3
from web_frontend import app

if __name__ == "__main__":
    app.run()
```

### 3. Reverse Proxy Configuration

#### Nginx Example

```nginx
location /fitness/ {
    proxy_pass http://127.0.0.1:5001/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

#### Apache Example

```apache
ProxyPass /fitness/ http://127.0.0.1:5001/
ProxyPassReverse /fitness/ http://127.0.0.1:5001/
ProxyPreserveHost On
```

### 4. Systemd Service (Linux)

Create `/etc/systemd/system/fitness-app.service`:

```ini
[Unit]
Description=Apple Fitness Advanced Workout Filter
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/apple-fitness-advanced-workout-filter
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/gunicorn --bind 127.0.0.1:5001 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable fitness-app
sudo systemctl start fitness-app
```

### 5. Run Commands

**Development:**

```bash
python web_frontend.py
```

**Production:**

```bash
gunicorn --bind 127.0.0.1:5001 wsgi:app
```

**With multiple workers:**

```bash
gunicorn --bind 127.0.0.1:5001 --workers 4 wsgi:app
```

### 6. Security Considerations

- Use HTTPS with your reverse proxy
- Consider adding basic auth if it contains personal data
- Set proper file permissions for the database
- Configure firewall rules to only allow local connections to port 5001
- Regularly backup your `fitness_cache.db` file

### 7. Database Backup

Consider setting up automatic backups:

```bash
# Daily backup cron job
0 2 * * * cp /path/to/fitness_cache.db /path/to/backups/fitness_cache_$(date +\%Y\%m\%d).db
```

This setup will run the Flask app behind your web server and make it accessible at `yourdomain.com/fitness/`.
