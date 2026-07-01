#!/bin/bash
# Start a single mock web app locally for the web-only harness.
# The Vite dev server serves both the UI and the state API (/post /go /state /upload).
#
# Usage: scripts/local/start_mock.sh [app] [port]
#   app   mock name without _mock suffix (default: gmail)
#   port  port to serve on (default: 5173)
set -e
APP="${1:-gmail}"
PORT="${2:-5173}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIR="$REPO/hub/websites/${APP}_mock"

[ -d "$DIR" ] || { echo "Error: $DIR not found. Did you run: git submodule update --init ?"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Error: npm not found (install Node.js)."; exit 1; }

cd "$DIR"
[ -d node_modules ] || { echo "Installing deps for ${APP}_mock..."; npm install --silent; }

echo "Starting ${APP}_mock at http://localhost:${PORT}  (state API: /go /post /state /upload)"
echo "Verify with:  curl -s 'http://localhost:${PORT}/go?sid=probe' | head -c 200"
exec npm run dev -- --port "$PORT" --host
