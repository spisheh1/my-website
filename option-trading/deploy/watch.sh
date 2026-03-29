#!/bin/bash
# =============================================================================
#  Options Trader — Auto-Deploy File Watcher
#  Watches the scripts/ folder and auto-deploys to EC2 whenever you save a file.
#
#  First time setup:
#    brew install fswatch        ← install the file watcher (once)
#    chmod +x deploy/watch.sh
#
#  Usage (from the "option trading" folder):
#    ./deploy/watch.sh
#
#  Press Ctrl+C to stop watching.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$ROOT_DIR/scripts"
DEPLOY_SCRIPT="$SCRIPT_DIR/deploy.sh"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; GRAY='\033[0;37m'; NC='\033[0m'

# ── Check fswatch is installed ────────────────────────────────────────────────
if ! command -v fswatch &>/dev/null; then
  echo ""
  echo "  fswatch is not installed. Install it with:"
  echo ""
  echo "    brew install fswatch"
  echo ""
  echo "  Then run this script again."
  exit 1
fi

# ── Check deploy script exists ────────────────────────────────────────────────
if [ ! -f "$DEPLOY_SCRIPT" ]; then
  echo "  deploy.sh not found at: $DEPLOY_SCRIPT"
  exit 1
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Options Trader — Auto-Deploy Watcher${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Watching: ${SCRIPTS_DIR}"
echo -e "  ${GRAY}Save any .py or .html file to trigger a deploy.${NC}"
echo -e "  ${GRAY}Press Ctrl+C to stop.${NC}"
echo ""

# ── Debounce: avoid multiple rapid deploys on multi-file saves ────────────────
LAST_DEPLOY=0
DEBOUNCE_SECS=3

deploy_now() {
  local NOW
  NOW=$(date +%s)
  local DIFF=$(( NOW - LAST_DEPLOY ))

  if [ "$DIFF" -lt "$DEBOUNCE_SECS" ]; then
    return  # too soon — skip
  fi

  LAST_DEPLOY=$NOW
  CHANGED_FILE="$1"
  FILENAME=$(basename "$CHANGED_FILE")

  echo ""
  echo -e "${YELLOW}[$(date '+%H:%M:%S')] Change detected: ${FILENAME}${NC}"
  bash "$DEPLOY_SCRIPT"
}

export -f deploy_now
export LAST_DEPLOY DEBOUNCE_SECS DEPLOY_SCRIPT GREEN YELLOW CYAN GRAY NC

# Watch .py and .html files; ignore __pycache__ and .pyc
fswatch \
  --event=Updated \
  --event=Created \
  --exclude='__pycache__' \
  --exclude='\.pyc$' \
  --include='\.py$' \
  --include='\.html$' \
  "$SCRIPTS_DIR" | while read -r CHANGED_FILE; do
    deploy_now "$CHANGED_FILE"
  done
