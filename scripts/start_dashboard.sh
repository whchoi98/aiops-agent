#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate
streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
