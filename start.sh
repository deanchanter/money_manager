#!/bin/bash

# Start both frontend and backend servers
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Start backend
(cd "$ROOT_DIR/backend" && source .venv/bin/activate && python main.py) &
BACKEND_PID=$!

# Start frontend
(cd "$ROOT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

# Handle cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:5173"
echo "Press Ctrl+C to stop both servers"

wait
