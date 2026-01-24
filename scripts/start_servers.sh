#!/bin/bash
# Linux startup script for Tank World

echo "========================================="
echo "Tank World - Server Startup"
echo "========================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Stop any existing servers
echo "Stopping any running servers..."
pkill -f "python.*backend.*main.py" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
sleep 2

echo ""
echo "Starting backend server..."
cd ../backend
python3 main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
cd ..

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Check if Node.js is available
if command -v npm &> /dev/null; then
    echo ""
    echo "Starting frontend server..."
    cd frontend
    npm run dev -- --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
    cd ..

    echo ""
    echo "========================================="
    echo "Servers started successfully!"
    echo "========================================="
    echo "Backend:  http://localhost:8000"
    echo "Frontend: http://localhost:5173"
    echo ""
    echo "From other devices, use:"
    IP=$(hostname -I | awk '{print $1}')
    echo "Backend:  http://$IP:8000"
    echo "Frontend: http://$IP:5173"
    echo ""
    echo "Logs:"
    echo "  Backend:  tail -f ../logs/backend.log"
    echo "  Frontend: tail -f ../logs/frontend.log"
else
    echo ""
    echo "========================================="
    echo "Backend started successfully!"
    echo "========================================="
    echo "Backend: http://localhost:8000"
    echo ""
    echo "From other devices, use:"
    IP=$(hostname -I | awk '{print $1}')
    echo "Backend: http://$IP:8000"
    echo ""
    echo "Note: Node.js not found, frontend not started."
    echo "You can access the backend from a browser on another machine."
    echo ""
    echo "Logs:"
    echo "  Backend: tail -f ../logs/backend.log"
fi

echo ""
echo "To stop servers, run: ./stop_servers.sh"
echo "========================================="
