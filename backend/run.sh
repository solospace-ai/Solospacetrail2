#!/bin/bash
# Run Solospace backend server

cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting Solospace backend..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
