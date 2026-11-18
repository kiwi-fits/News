#!/bin/bash
# One-click stopper for AI Tamil News Reels Studio
echo "🛑 Stopping AI Tamil News Reels Studio..."
lsof -ti :5001 | xargs kill -9 2>/dev/null || true
lsof -ti :5002 | xargs kill -9 2>/dev/null || true
pkill -f "app.py" 2>/dev/null || true
echo "✅ AI Studio stopped successfully!"
sleep 1
