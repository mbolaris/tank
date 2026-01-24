#!/bin/bash
# Linux stop script for Tank World

echo "Stopping Tank World servers..."

# Kill backend
pkill -f "python.*backend.*main.py"
echo "Backend stopped."

# Kill frontend
pkill -f "node.*vite"
echo "Frontend stopped."

# Wait for processes to end
sleep 1

echo "All servers stopped."
