#!/bin/bash
# Starts the app and opens it in a fresh Chrome Incognito window, so browser autofill/history
# from previous practice runs never shows up. Ctrl+C stops the server cleanly.
cd "$(dirname "$0")"

./venv/bin/streamlit run app.py --server.headless true --server.port 8501 &
STREAMLIT_PID=$!
trap "kill $STREAMLIT_PID 2>/dev/null" EXIT INT TERM

sleep 2
open -na "Google Chrome" --args --incognito "http://localhost:8501"

wait $STREAMLIT_PID
