#!/bin/bash
# One-click stopper for AI Tamil News Reels Studio
cd "$(dirname "$0")"
echo "🛑 Stopping AI Tamil News Reels Studio..."

# Handover control to Cloud runner immediately
./.venv/bin/python -c "from heartbeat import mark_offline_and_sync; mark_offline_and_sync()" 2>/dev/null || true

lsof -ti :5001 | xargs kill -9 2>/dev/null || true
lsof -ti :5002 | xargs kill -9 2>/dev/null || true
pkill -f "app.py" 2>/dev/null || true
echo "✅ Local server stopped! Cloud Runner will take over in GitHub Actions."
sleep 1
