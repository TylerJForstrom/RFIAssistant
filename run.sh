#!/bin/bash

echo "Starting Smart RFI Assistant..."

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

mkdir -p data/raw
mkdir -p data/processed

if [ ! -f "data/raw/rfis.csv" ]; then
  echo "No dataset found. Creating sample data..."
  python3 scripts/create_sample_data.py
fi

lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null

echo "Starting FastAPI on port 8000..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend to be ready..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health >/dev/null; then
    echo "Backend is ready."
    break
  fi
  sleep 1
done

if ! curl -s http://127.0.0.1:8000/health >/dev/null; then
  echo "Backend failed to start in time."
  kill $BACKEND_PID 2>/dev/null
  exit 1
fi

echo "Starting Streamlit on port 8501..."
streamlit run ui/streamlit_app.py --server.port 8501 &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://localhost:8501"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
