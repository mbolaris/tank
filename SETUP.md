# Tank World - Setup Instructions

## Agent & Contributor Quickstart (Recommended for AI Agents / Devs)

If you are an AI agent or a developer preparing to contribute improvements:

```bash
# 1. Setup dev dependencies
pip install -e .[dev]

# 2. Run the smoke gate to verify everything is working (under 30 seconds)
python tools/smoke_gate.py

# 3. Use the agent gate for local validation (under 90 seconds)
python tools/agent_gate.py

# 4. Use the pre-PR gate before submitting a PR (under 3 minutes)
python tools/pre_pr_gate.py
```

For detailed setup or troubleshooting, follow the normal setup paths below.

---

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
    python start.py
    ```
    - Web UI → http://localhost:3000
    - Backend API → http://localhost:8000 (docs at `/docs`)

    This starts both the backend and frontend dev servers in parallel, streaming their logs. Press `Ctrl+C` to stop both.

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

You can launch both the FastAPI backend and the Vite React frontend with a single command:

```bash
python start.py
```

This will run pre-flight checks, install dependencies if missing, start both servers in parallel with colored output logging, and open your browser automatically.

*(Alternatively, you can run them in separate terminals: run `python main.py` for the backend, and run `cd frontend && npm run dev` to start the frontend).*

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

   ```bash
   python start.py
   ```
   This single command handles pre-flight verification, runs both the backend and frontend dev servers, and launches the browser at http://localhost:3000.

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

## Viewing Soccer Mode

Soccer mode is now watchable end-to-end in the web UI:

1. **Start the application** (as described above)
2. **Open Network Dashboard** at http://localhost:3000
3. **Open any world** by clicking on it
4. **Switch to Soccer mode** using the mode selector dropdown and choosing "Soccer Pitch"
5. **Watch players chase and kick the ball** - animation should be continuous

Soccer uses autopolicy: players automatically move toward the ball and kick toward their opponent's goal. The left team kicks toward the right goal (+x direction), and the right team kicks toward the left goal (-x direction).
