#!/bin/bash
# Daily Dashboard Generator
# Run: bash skills/daily-dashboard/generate.sh

DASHBOARD_DIR="/home/yat121/.openclaw/workspace/skills/daily-dashboard"
DATA_DIR="$DASHBOARD_DIR/data"
OUTPUT="$DASHBOARD_DIR/index.html"

mkdir -p "$DATA_DIR"

echo "=== Fetching Weather ==="
curl -s "wttr.in/Hong+Kong?format=j1" -o "$DATA_DIR/weather.json"
echo "Done"

echo "=== Fetching Crypto Prices ==="
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true" -o "$DATA_DIR/crypto.json" 2>/dev/null || echo '{}' > "$DATA_DIR/crypto.json"
echo "Done"

echo "=== Fetching News ==="
curl -s --max-time 10 "https://hn.algolia.com/api/v1/search?query=crypto+bitcoin+ethereum&tags=story&hitsPerPage=5" -o "$DATA_DIR/news.json" 2>/dev/null || echo '{}' > "$DATA_DIR/news.json"
echo "Done"

echo "=== Generating HTML ==="
/usr/bin/python3 "$DASHBOARD_DIR/generate.py"
echo "Done: $OUTPUT"
