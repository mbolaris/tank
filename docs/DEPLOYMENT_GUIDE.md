# Deployment Guide - React Web UI

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm 9+

### Terminal 1: Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```
Backend runs on: `http://localhost:8000`

### Terminal 2: Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on: `http://localhost:5173`

### Access
Open browser to: `http://localhost:5173`

## Production Deployment

### Option 1: Separate Backend + Frontend (Recommended)

#### Backend Deployment (Python/FastAPI)

**1. Install Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**2. Configure Environment**
```bash
# Create .env file
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=https://your-frontend-domain.com
```

**3. Update CORS in main.py**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Restrict to your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**4. Run with Production Server**
```bash
# Using Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# Using Gunicorn (recommended)
gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**5. Deploy Options**
- **Docker**: Use provided Dockerfile (see below)
- **Heroku**: `heroku create && git push heroku main`
- **Railway**: Connect GitHub repo, auto-deploy
- **Render**: Add as web service
- **AWS EC2**: Install Python, clone repo, run with systemd
- **DigitalOcean**: App Platform or Droplet

#### Frontend Deployment (React/Vite)

**1. Update WebSocket URL**
Edit `frontend/src/hooks/useWebSocket.ts`:
```typescript
const WS_URL = 'wss://your-backend-domain.com/ws';  // Use wss:// for HTTPS
```

**2. Build for Production**
```bash
cd frontend
npm run build
```

**3. Deploy Static Files**
Upload `dist/` directory to:
- **Netlify**: Drag & drop `dist/` folder
- **Vercel**: `vercel --prod`
- **GitHub Pages**: Push `dist/` to `gh-pages` branch
- **AWS S3**: `aws s3 sync dist/ s3://your-bucket --acl public-read`
- **Cloudflare Pages**: Connect repo, auto-deploy
- **Nginx**: Copy `dist/` to `/var/www/html`

**4. Configure Web Server**

**Nginx Example:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/www/html/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

### Option 2: Docker Deployment (All-in-One)

**Create `Dockerfile.backend`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY core/ /app/core/
COPY simulation_engine.py .
COPY movement_strategy.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Create `Dockerfile.frontend`:**
```dockerfile
FROM node:18-alpine AS build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Create `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    environment:
      - BACKEND_URL=http://backend:8000
    restart: unless-stopped
```

**Deploy:**
```bash
docker-compose up -d
```

## Environment Configuration

### Backend Environment Variables
```bash
# .env file
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
MAX_POPULATION=100
FRAME_RATE=30
```

### Frontend Environment Variables
```bash
# .env.production
VITE_WS_URL=wss://your-backend.com/ws
VITE_API_URL=https://your-backend.com
```

## Security Checklist

### Backend Security
- [ ] Restrict CORS to specific frontend domain
- [ ] Add rate limiting for commands (optional)
- [ ] Use HTTPS (wss://) for WebSocket
- [ ] Add WebSocket authentication (optional)
- [ ] Enable firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable logging and monitoring

### Frontend Security
- [ ] Use HTTPS
- [ ] Configure Content Security Policy
- [ ] Enable CORS only for backend domain
- [ ] Minify and optimize bundles
- [ ] Remove console.logs in production

## Performance Optimization

### Backend
- [x] Running simulation in background thread (30 FPS)
- [x] Efficient JSON serialization (~3.3KB per frame)
- [ ] Add connection pooling if needed
- [ ] Consider Redis for state caching if scaling

### Frontend
- [x] Code splitting with Vite
- [x] Gzipped bundles (63.7KB JS)
- [x] Auto-reconnect WebSocket
- [ ] Add service worker for offline support
- [ ] Implement lazy loading for large screens

## Monitoring & Logging

### Backend Monitoring
```python
# Add to main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log WebSocket connections
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info(f"Client connected: {websocket.client}")
    # ... rest of code
```

### Frontend Monitoring
```typescript
// Add error tracking (e.g., Sentry)
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: "production"
});
```

## Scaling Considerations

### Single Server (Up to 100 connections)
- Current setup handles well
- No changes needed

### Multiple Servers (100+ connections)
- Use Redis for shared state
- Add load balancer
- Implement session affinity for WebSocket

### High Traffic (1000+ connections)
- Consider separate simulation instances
- Use message queue (RabbitMQ/Redis)
- Implement horizontal scaling

## Troubleshooting

### Backend Won't Start
```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check port availability
lsof -i :8000
```

### Frontend Won't Build
```bash
# Clear node_modules
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

### WebSocket Connection Failed
1. Check backend is running on port 8000
2. Verify CORS settings allow frontend domain
3. Check firewall rules
4. Use browser DevTools → Network → WS tab
5. Ensure using `wss://` with HTTPS

### Simulation Running Slow
1. Check CPU usage (should be <20%)
2. Verify FPS in stats panel (should be ~30)
3. Reduce max population if needed
4. Check backend logs for errors

## Health Checks

### Backend Health
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","simulation_running":true,...}
```

### Frontend Health
```bash
curl http://localhost:5173/
# Should return HTML
```

### WebSocket Test
```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));
```

## Backup & Recovery

### Backup Simulation State
```python
# TODO: Implement save/load
# Current state is ephemeral (resets on restart)
```

### Recovery Plan
1. Backend crashes → Auto-restart with systemd/PM2
2. Frontend crashes → Nginx serves cached version
3. WebSocket disconnects → Auto-reconnect (3s delay)

## Maintenance

### Update Backend
```bash
cd backend
git pull
pip install -r requirements.txt
sudo systemctl restart fishtank-backend
```

### Update Frontend
```bash
cd frontend
git pull
npm install
npm run build
# Deploy new dist/ folder
```

## Cost Estimation

### Free Tier (Development)
- **Netlify**: Frontend hosting (free)
- **Render**: Backend hosting (free tier)
- **Total**: $0/month

### Production (Small Scale)
- **DigitalOcean Droplet**: $6/month (1GB RAM)
- **Cloudflare**: Free CDN
- **Total**: $6/month

### Production (Medium Scale)
- **AWS EC2**: $20/month (t3.small)
- **AWS S3**: $5/month (frontend)
- **AWS CloudFront**: $10/month (CDN)
- **Total**: $35/month

## Support

### Documentation
- Backend API: `backend/README.md`
- Frontend: `frontend/README.md`
- Main Guide: `WEB_UI_README.md`
- Testing: `TESTING_REPORT.md`

### Logs
- Backend: `uvicorn.log` or systemd journal
- Frontend: Browser DevTools console
- WebSocket: Browser DevTools → Network → WS tab

---

**Last Updated:** November 16, 2025
**Version:** 1.0.0
**Status:** Production Ready ✅
