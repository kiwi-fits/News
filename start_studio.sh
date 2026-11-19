#!/usr/bin/env bash
# ========================================================
# AI Tamil News Reels Studio Launcher
# ========================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

# Sync newest cloud history & seen articles before starting
git pull origin main --quiet || true

echo "=========================================================="
echo "🎬 Starting AI Tamil News Reels Studio"
echo "💻 Studio URL: http://localhost:5001"
echo "🎙️ Voice:      Tamil Male Anchor (Valluvar)"
echo "📱 Output:     1080x1920 (9:16 Vertical Facebook Reels)"
echo "=========================================================="

exec "$VENV_PYTHON" app.py
