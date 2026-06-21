#!/usr/bin/env bash
set -euo pipefail

echo "=== StoryUI2Test Setup ==="

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r interface/requirements.txt

python -m spacy download pt_core_news_sm

echo ""
echo "Setup complete!"
echo "Activate the environment and run:"
echo "  source .venv/bin/activate"
echo "  streamlit run interface/home.py"
