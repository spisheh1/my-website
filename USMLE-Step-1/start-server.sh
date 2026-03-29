#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  USMLE Step 1 — Smart Cross-Platform Server Launcher
#  Works on: macOS, Ubuntu / Debian Linux
#
#  Usage:
#    chmod +x start-server.sh   (first time only)
#    ./start-server.sh
#
#  Logic:
#    1. Compute MD5 of step1.html  →  "current version"
#    2. If server already running with the SAME version  →  just open browser
#    3. If server running with a DIFFERENT version       →  backup old HTML,
#                                                           stop old server,
#                                                           start new one
#    4. If server not running at all                     →  start fresh
#
#  Files created in this directory:
#    .server.pid      — PID of the running python server
#    .server.version  — MD5 hash of the HTML it is serving
#    backups/         — old step1.html copies, one per version
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Constants ──────────────────────────────────────────────────────────────
PORT=8765
HTML_FILE="step1.html"
PID_FILE=".server.pid"
VER_FILE=".server.version"
BACKUP_DIR="backups"
URL="http://localhost:${PORT}/${HTML_FILE}"

# ── Change to the directory containing this script ────────────────────────
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colour helpers ─────────────────────────────────────────────────────────
BOLD=$'\e[1m'; RESET=$'\e[0m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; CYAN=$'\e[36m'; RED=$'\e[31m'
info()    { echo "${CYAN}▶ ${RESET}$*"; }
success() { echo "${GREEN}✓ ${RESET}${BOLD}$*${RESET}"; }
warn()    { echo "${YELLOW}⚠ ${RESET}$*"; }
error()   { echo "${RED}✗ ${RESET}${BOLD}$*${RESET}"; }
banner()  {
  echo ""
  echo "${BOLD}╔══════════════════════════════════════════╗${RESET}"
  echo "${BOLD}║    USMLE Step 1 — Server Launcher        ║${RESET}"
  echo "${BOLD}╚══════════════════════════════════════════╝${RESET}"
  echo ""
}

# ── Compute MD5 (macOS uses `md5 -q`, Linux uses `md5sum`) ────────────────
compute_md5() {
  if command -v md5sum &>/dev/null; then
    md5sum "$1" | awk '{print $1}'
  elif command -v md5 &>/dev/null; then
    md5 -q "$1"
  else
    # Fallback: use Python (always available if the server can run)
    python3 -c "import hashlib,sys; print(hashlib.md5(open(sys.argv[1],'rb').read()).hexdigest())" "$1"
  fi
}

# ── Check if a PID is alive ────────────────────────────────────────────────
pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# ── Open browser (macOS: open, Linux: xdg-open / sensible-browser) ─────────
open_browser() {
  local url="$1"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    (sleep 1.2 && open -a "Google Chrome" "$url" 2>/dev/null \
      || open "$url") &
  else
    if command -v xdg-open &>/dev/null; then
      (sleep 1.2 && xdg-open "$url") &
    elif command -v sensible-browser &>/dev/null; then
      (sleep 1.2 && sensible-browser "$url") &
    else
      warn "Cannot auto-open browser. Navigate to: ${BOLD}${url}${RESET}"
    fi
  fi
}

# ── Start the Python HTTP server ───────────────────────────────────────────
start_server() {
  if command -v python3 &>/dev/null; then
    python3 -m http.server "$PORT" &>/dev/null &
  elif command -v python &>/dev/null; then
    python -m SimpleHTTPServer "$PORT" &>/dev/null &
  else
    error "Python not found. Install Python from https://python.org"
    exit 1
  fi
  echo $! > "$PID_FILE"
  echo "$CURRENT_VER" > "$VER_FILE"
  success "Server started  (PID $(cat "$PID_FILE"))"
}

# ── Stop a running server by PID ───────────────────────────────────────────
stop_server() {
  local pid="$1"
  info "Stopping old server (PID ${pid})…"
  kill "$pid" 2>/dev/null || true
  # Give it up to 3 seconds to exit cleanly
  for _ in 1 2 3; do
    sleep 1
    pid_alive "$pid" || break
  done
  # Force-kill if still alive
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE" "$VER_FILE"
  success "Old server stopped."
}

# ── Backup the running HTML version ───────────────────────────────────────
backup_html() {
  local old_ver="$1"
  mkdir -p "$BACKUP_DIR"
  local backup_path="${BACKUP_DIR}/step1_v${old_ver}.html"
  if [[ ! -f "$backup_path" ]]; then
    cp "$HTML_FILE" "$backup_path"
    info "Old HTML backed up → ${BACKUP_DIR}/step1_v${old_ver:0:8}…html"
  else
    info "Backup for v${old_ver:0:8}… already exists — skipping copy."
  fi
}

# ── Cleanup trap (Ctrl+C) ─────────────────────────────────────────────────
cleanup() {
  echo ""
  info "Shutting down…"
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || true)
    if pid_alive "$pid"; then
      kill "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$PID_FILE" "$VER_FILE"
  success "Server stopped. Goodbye!"
  exit 0
}
trap cleanup INT TERM

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

banner

# Guard: step1.html must exist
if [[ ! -f "$HTML_FILE" ]]; then
  error "${HTML_FILE} not found in $(pwd)"
  error "Run this script from the USMLE-Step-1 folder."
  exit 1
fi

# 1. Compute current version
info "Computing version fingerprint…"
CURRENT_VER=$(compute_md5 "$HTML_FILE")
info "Current HTML version: ${BOLD}${CURRENT_VER:0:8}…${RESET}"

# 2. Read stored state
STORED_PID=""
STORED_VER=""
if [[ -f "$PID_FILE" ]]; then STORED_PID=$(cat "$PID_FILE" 2>/dev/null || true); fi
if [[ -f "$VER_FILE" ]]; then STORED_VER=$(cat "$VER_FILE" 2>/dev/null || true); fi

SERVER_ALIVE=false
if pid_alive "$STORED_PID"; then SERVER_ALIVE=true; fi

# ── Decision tree ──────────────────────────────────────────────────────────

if $SERVER_ALIVE; then
  if [[ "$STORED_VER" == "$CURRENT_VER" ]]; then
    # ── Case A: running, same version ─────────────────────────────────────
    success "Server already running with the current version (PID ${STORED_PID})."
    info "Opening browser → ${URL}"
    open_browser "$URL"
    echo ""
    echo "  ${BOLD}→ Keep this terminal open to keep the server running${RESET}"
    echo "  ${BOLD}→ Press Ctrl+C here to stop${RESET}"
    echo ""
    # Wait so the terminal (if double-clicked) doesn't close immediately
    wait "$STORED_PID" 2>/dev/null || true

  else
    # ── Case B: running, different version → upgrade ───────────────────────
    warn "HTML has changed! Old version: ${BOLD}${STORED_VER:0:8}…${RESET}"
    backup_html "$STORED_VER"
    stop_server "$STORED_PID"
    echo ""
    info "Starting server with new version…"
    start_server
    open_browser "$URL"
    success "Upgraded to new version — browser opening at ${URL}"
    echo ""
    echo "  ${BOLD}→ Keep this terminal open to keep the server running${RESET}"
    echo "  ${BOLD}→ Press Ctrl+C here to stop${RESET}"
    echo ""
    wait "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null || true
  fi

else
  # ── Case C: server not running (or stale PID) ──────────────────────────
  # Clean up stale files if any
  if [[ -n "$STORED_PID" ]] && ! $SERVER_ALIVE; then
    warn "Stale PID ${STORED_PID} found (process gone). Cleaning up."
    rm -f "$PID_FILE" "$VER_FILE"
  fi

  # Check if the port is blocked by something we didn't start
  PORT_BLOCKED=false
  if command -v lsof &>/dev/null; then
    lsof -ti:"$PORT" &>/dev/null && PORT_BLOCKED=true || true
  elif command -v fuser &>/dev/null; then
    fuser "$PORT"/tcp &>/dev/null && PORT_BLOCKED=true || true
  fi

  if $PORT_BLOCKED; then
    warn "Port ${PORT} is in use by another process — freeing it…"
    if command -v lsof &>/dev/null; then
      lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
    elif command -v fuser &>/dev/null; then
      fuser -k "$PORT"/tcp 2>/dev/null || true
    fi
    sleep 0.5
  fi

  info "Starting server…"
  start_server
  sleep 0.3   # brief pause so the server is ready before the browser hits it
  open_browser "$URL"
  success "Server running at ${BOLD}${URL}${RESET}"
  echo ""
  echo "  ${BOLD}→ Keep this terminal open to keep the server running${RESET}"
  echo "  ${BOLD}→ Press Ctrl+C here to stop${RESET}"
  echo ""
  wait "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null || true
fi
