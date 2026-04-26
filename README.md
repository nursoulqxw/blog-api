# Blog API

A Django REST API with real-time WebSocket support, Celery background tasks, and nginx as a reverse proxy — all running in Docker Compose.

## Stack

- **Django 6 + DRF** — REST API
- **Daphne + Django Channels** — ASGI server, WebSocket support
- **Celery + Celery Beat** — background and scheduled tasks
- **Redis** — message broker, channel layer, cache
- **nginx** — reverse proxy, static/media file serving
- **SQLite** — database (persisted in a Docker volume)
- **Flower** — Celery task monitor

## Architecture

```
Browser / curl
      │ :80
      ▼
  ┌────────┐
  │ nginx  │  serves /static/ and /media/ directly
  └───┬────┘
      │ proxy_pass
      ▼
  ┌────────┐
  │daphne  │ :8000 (not published to host)
  │  web   │
  └────────┘
      │
  redis, celery_worker, celery_beat, flower
```

Only port 80 (nginx) and port 5555 (Flower) are reachable from the host. Port 8000 is internal only.

## Running

```bash
docker compose up --build
```

On first run the entrypoint automatically runs migrations, collectstatic, and compiles translations. To seed the database with sample posts and users:

```bash
docker compose exec web python manage.py seed
```

## API

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| POST | `/api/auth/register/` | Register a new user |
| GET | `/api/posts/` | List published posts |
| GET | `/api/posts/<slug>/` | Post detail |
| GET/POST | `/api/posts/<slug>/comments/` | List or create comments |
| GET | `/api/stats/` | Blog statistics |
| WS | `/ws/posts/<slug>/comments/` | Live comment stream |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/redoc/` | ReDoc |

Authentication uses JWT. Pass the token as a query parameter for WebSocket connections:

```
ws://localhost/ws/posts/<slug>/comments/?token=<access_token>
```

## Verification (HW4 checks)

**1. nginx is the entry point, returns 200**

```bash
curl -I http://localhost/admin/login/
# HTTP/1.1 200 OK
# Server: nginx/1.27.5
```

**2. Static files served by nginx with long cache**

```bash
curl -I http://localhost/static/admin/css/base.css
# HTTP/1.1 200 OK
# Cache-Control: max-age=5788800
```

**3. API returns JSON**

```bash
curl http://localhost/api/posts/
# [...] JSON array of posts
```

**4. Stopping web produces 502 from nginx, not connection refused**

```bash
docker compose stop web
curl -I http://localhost/api/posts/
# HTTP/1.1 502 Bad Gateway
# Server: nginx/1.27.5

docker compose start web
```

**5. Port 8000 is not reachable from the host**

```bash
curl http://localhost:8000/
# curl: (7) Failed to connect to localhost port 8000
```

**6. WebSocket upgrades with 101**

Get a token first:

```bash
TOKEN=$(curl -s -X POST http://localhost/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@blog.local","password":"Alicepass1!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```

Connect:

```bash
python3 << EOF
import asyncio, websockets

async def test():
    uri = f"ws://localhost/ws/posts/hello-world/comments/?token=$TOKEN"
    async with websockets.connect(uri) as ws:
        print("Connected — 101 Switching Protocols confirmed")

asyncio.run(test())
EOF
```

Or with wscat if available:

```bash
wscat -c "ws://localhost/ws/posts/hello-world/comments/?token=$TOKEN"
```
