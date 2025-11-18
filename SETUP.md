# Fish Tank Simulation - Setup Instructions

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

After installing dependencies, you can start the application:

```bash
# From the root tank/ directory
python main.py
```

This will start both:
- Backend API server on http://localhost:8000
- Frontend dev server on http://localhost:3000

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

   pip install -r requirements.txt
   ```

3. **Install Frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open browser**
   - Visit http://localhost:3000

## Troubleshooting

### Blank UI / White Screen
- **Cause**: Frontend dependencies not installed
- **Fix**: Run `npm install` in the `frontend` directory

### Connection Error / "Waiting" Status
- **Cause**: Backend server not running
- **Fix**: Make sure `python main.py` is running and check http://localhost:8000/health

### Port Already in Use
- **Cause**: Another process is using port 3000 or 8000
- **Fix**: Kill the other process or change the port in `vite.config.ts` (frontend) or `core/constants.py` (backend)

### Module Not Found Errors
- **Cause**: Python dependencies not installed
- **Fix**: Run `pip install -r requirements.txt`

## Development

- Frontend uses Vite for hot module reloading (changes auto-refresh)
- Backend uses FastAPI with WebSocket for real-time updates
- Both servers need to be running for the app to work

## Tech Stack

- **Frontend**: React 19, TypeScript, Vite
- **Backend**: Python, FastAPI, WebSocket
- **Simulation**: Custom physics engine with neural networks
