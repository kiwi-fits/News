#!/bin/bash
# One-click launcher for AI Tamil News Reels Studio
cd "$(dirname "$0")"
echo "🎬 Starting AI Tamil News Reels Studio..."
sleep 2 && open "http://localhost:5001" &
./start_studio.sh
