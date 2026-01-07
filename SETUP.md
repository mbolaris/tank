# Fish Tank Simulation - Setup Instructions

## macOS Quick Install (Sonoma / Apple Silicon)

1. **Install Command Line Tools (once per machine)**
   ```bash
   xcode-select --install
   ```
2. **Install Homebrew + runtimes**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   brew install python@3.12 node@22
   ```
   > Use `brew info python@3.12` for activation instructions if it is not your default `python3`.
3. **Create & activate a virtualenv**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```
4. **Install backend dependencies from `pyproject.toml`**
   ```bash
   pip install -e .
   ```
   This installs FastAPI, Uvicorn (with websockets), orjson, and other required simulation packages in one shot.
5. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```
6. **Run everything**
   ```bash
   # From repo root
   python3 main.py
   ```
   - Backend API → http://localhost:8000 (docs at `/docs`)
   - Frontend (Vite) → http://localhost:3000

Keeping a dedicated terminal tab running `python3 main.py` and another running `npm run dev` helps catch log output quickly.

## Problem: Blank UI

If you're seeing a blank UI when you visit http://localhost:3000, it's likely because the frontend dependencies haven't been installed.

## Solution

### Step 1: Install Frontend Dependencies

Before running the frontend dev server, you must install the npm dependencies:

```bash
cd frontend
npm install
```

This will install all required packages including React, Vite, and other dependencies into the `node_modules` directory.

### Step 2: Start the Application

You need to run the backend and frontend in separate terminals.

**Terminal 1 (Backend):**
```bash
# From the root tank/ directory
python3 main.py
```

**Terminal 2 (Frontend):**
```bash
# From the root tank/ directory
cd frontend
npm run dev
```

### Step 3: Open Browser

Visit http://localhost:3000 in your browser. You should now see the Fish Tank Simulation UI.

## Full Setup Steps (First Time)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tank
   ```

2. **Install Python dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac

   # Preferred: read dependencies from pyproject
   pip install -e .
   ```

3. **Install Frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Run the application**

   **Terminal 1:**
   ```bash
   python3 main.py
   ```

   **Terminal 2:**
   ```bash
   cd frontend
   npm run dev
   ```

5. **Open browser**
   - Visit http://localhost:3000

## Troubleshooting

### Extensive Logs / High CPU on Startup
- **Cause**: The server is restoring many old simulations found in `data/tanks`. This often happens if test runs created persistent snapshots.
- **Fix**: Stop the server and delete the `data/tanks` directory to start fresh:
  ```bash
  rm -rf data/tanks/*
  ```

### Blank UI / White Screen
- **Cause**: Frontend dependencies not installed or frontend server not running
- **Fix**: Run `npm install` in `frontend/`, then `npm run dev`

### Connection Error / "Waiting" Status
- **Cause**: Backend server not running
- **Fix**: Make sure `python main.py` is running and check http://localhost:8000/health

### Port Already in Use
- **Cause**: Another process is using port 3000 or 8000
- **Fix**: Kill the other process or change the port in `vite.config.ts` (frontend) or `core/constants.py` (backend)

### Module Not Found Errors
- **Cause**: Python dependencies not installed
- **Fix**: Run `pip install -e .`

## Development

- Frontend uses Vite for hot module reloading (changes auto-refresh)
- Backend uses FastAPI with WebSocket for real-time updates
- Both servers need to be running for the app to work

## Tech Stack

- **Frontend**: React 19, TypeScript, Vite
- **Backend**: Python, FastAPI, WebSocket
- **Simulation**: Custom physics engine with neural networks
