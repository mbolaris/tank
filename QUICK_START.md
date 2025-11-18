# 🚀 Quick Start Guide

## Problem: Blank UI in Browser?

If you're seeing a blank page, you need to run **BOTH** the backend AND frontend servers!

## ✅ Solution: Run Both Servers

### Option 1: Automatic Startup (Recommended)

```bash
# From the tank/ directory, run:
./start-app.sh
```

This will start both servers automatically. Then open **http://localhost:3000** in your browser.

### Option 2: Manual Startup (Two Terminals)

**Terminal 1 - Backend:**
```bash
# From tank/ directory
python main.py
```

**Terminal 2 - Frontend:**
```bash
# From tank/ directory
cd frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

## 🌐 Important URLs

- **Frontend (USE THIS)**: http://localhost:3000 ← **Open this in your browser!**
- **Backend API**: http://localhost:8000 (don't open this directly)
- **WebSocket**: ws://localhost:8000/ws (used by frontend automatically)

## ⚠️ Common Mistakes

❌ **Don't access** `http://localhost:8000` directly - this is just the API backend!
✅ **Do access** `http://localhost:3000` - this is your frontend application!

## 📋 Checklist

Before running, make sure you've installed dependencies:

```bash
# Install Python dependencies (from tank/ directory)
pip install -e .

# Install frontend dependencies (from tank/frontend/ directory)
cd frontend
npm install
cd ..
```

## 🐛 Troubleshooting

### Still seeing blank page?

1. **Check both servers are running:**
   - Backend should show: `Uvicorn running on http://0.0.0.0:8000`
   - Frontend should show: `Local: http://localhost:3000/`

2. **Check browser console for errors:**
   - Press F12 in your browser
   - Look at the Console tab for any error messages

3. **Verify you're on the right URL:**
   - Make sure you're accessing `http://localhost:3000`, not `http://localhost:8000`

4. **Check WebSocket connection:**
   - In browser console, you should see WebSocket connecting to `ws://localhost:8000/ws`
   - Status should show "Connected" in the UI

### Port already in use?

If you get "port already in use" errors:

```bash
# Kill processes on port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Kill processes on port 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

## 🎮 Once It's Running

You should see:
- 🐠 Swimming fish in the tank
- 📊 Statistics panel on the right
- 🎛️ Control buttons (Add Food, Pause, Reset)
- 🎴 Poker events when fish play poker
- 🔴 "Connected" status indicator

Enjoy the simulation! 🌊✨
