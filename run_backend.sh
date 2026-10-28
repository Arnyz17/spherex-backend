#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "=========================================================="
echo " Starting SPHEREx Mission Data Analysis Backend Service"
echo " Interactive API Docs: http://localhost:8000/docs"
echo " Alternative ReDoc:   http://localhost:8000/redoc"
echo "=========================================================="

export PYTHONPATH=.
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
