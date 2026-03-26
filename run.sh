#!/bin/bash

echo "🚀 Starting Smart RFI Assistant..."

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found. Run: python3 -m venv .venv"
    exit 1
fi

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "🧹 Cleaning up old processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null

echo "🔧 Starting FastAPI backend..."
uvicorn app.main:app --reload &
BACKEND_PID=$!

sleep 3

echo "🎨 Starting Streamlit frontend..."
PYTHONPATH=. streamlit run ui/streamlit_app.py &
FRONTEND_PID=$!

echo ""
echo "✅ App is running:"
echo "👉 Backend: http://127.0.0.1:8000"
echo "👉 Frontend: http://localhost:8501"
echo ""
echo "Press CTRL+C to stop everything."

wait $BACKEND_PID $FRONTEND_PID
