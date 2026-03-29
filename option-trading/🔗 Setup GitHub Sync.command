#!/bin/bash
# =============================================================================
#  Setup GitHub Sync — run this ONCE to connect to GitHub
#  After this, every deploy will automatically commit + push your code.
#
#  Repo  : https://github.com/spisheh1/my-website.git
#  Folder: option-trading/  (inside the repo)
# =============================================================================

cd "$(dirname "$0")"

OPTION_TRADING_DIR="$(pwd)"                          # …/option-trading/
REPO_ROOT="$(dirname "$OPTION_TRADING_DIR")"          # one level up — git root
FOLDER_NAME="$(basename "$OPTION_TRADING_DIR")"       # "option-trading"
GITHUB_URL="https://github.com/spisheh1/my-website.git"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

clear
echo ""
echo "  ┌──────────────────────────────────────────────────┐"
echo "  │   Options Trader  ·  GitHub Sync Setup           │"
echo "  │   Repo   : spisheh1/my-website                   │"
echo "  │   Folder : option-trading/                       │"
echo "  └──────────────────────────────────────────────────┘"
echo ""
echo -e "  Git root will be: ${CYAN}${REPO_ROOT}${NC}"
echo ""

# ── Step 1: Ask for GitHub Personal Access Token ──────────────────────────────
echo -e "${YELLOW}[1/5] GitHub Personal Access Token${NC}"
echo ""
echo "  You need a token to push to GitHub. To create one:"
echo "  1. Go to → github.com → Settings → Developer settings"
echo "  2. Personal access tokens → Tokens (classic) → Generate new token"
echo "  3. Give it a name (e.g. 'options-trader'), check the 'repo' box"
echo "  4. Copy the token (starts with 'ghp_…')"
echo ""
echo -n "  Paste your GitHub token here (input hidden): "
read -rs GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "${RED}✗ No token entered. Exiting.${NC}"
  echo ""; echo "  Press any key to close…"; read -rn 1; exit 1
fi

# ── Step 2: Store token in git credential store ───────────────────────────────
echo ""
echo -e "${YELLOW}[2/5] Saving credentials…${NC}"

# Use macOS Keychain if available, otherwise file-based store
if git credential-osxkeychain 2>/dev/null; then
  git config --global credential.helper osxkeychain
  # Feed credentials to osxkeychain
  printf "protocol=https\nhost=github.com\nusername=spisheh1\npassword=%s\n" "$GITHUB_TOKEN" \
    | git credential-osxkeychain store 2>/dev/null
  echo -e "  ${GREEN}✓ Saved to macOS Keychain${NC}"
else
  # Fallback: embed token in the remote URL (stored in .git/config, not in code)
  git config --global credential.helper store
  printf "https://spisheh1:%s@github.com\n" "$GITHUB_TOKEN" >> "$HOME/.git-credentials"
  chmod 600 "$HOME/.git-credentials"
  echo -e "  ${GREEN}✓ Saved to ~/.git-credentials${NC}"
fi

# Also save token to a local config file for deploy script use
TOKEN_FILE="$REPO_ROOT/.git-token"
echo "$GITHUB_TOKEN" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"

# ── Step 3: Create root .gitignore (only tracks option-trading/, nothing else) ─
echo ""
echo -e "${YELLOW}[3/5] Creating root .gitignore…${NC}"

cat > "$REPO_ROOT/.gitignore" << 'GITIGNORE'
# Ignore everything at the repo root by default
# Only the option-trading/ subfolder is tracked
*
!.gitignore
!option-trading/
!option-trading/**

# ── Secrets (never commit these, even inside option-trading/) ──────────────────
option-trading/.env
option-trading/*.pem
option-trading/*.key
option-trading/secrets.json
option-trading/.git-token

# ── Databases (live trade data stays local) ────────────────────────────────────
option-trading/**/*.db
option-trading/**/*.sqlite
option-trading/**/*.sqlite3

# ── Python cache ──────────────────────────────────────────────────────────────
option-trading/**/__pycache__/
option-trading/**/*.pyc
option-trading/**/*.pyo
option-trading/**/venv/
option-trading/**/.venv/

# ── Node / iOS ────────────────────────────────────────────────────────────────
option-trading/**/node_modules/
option-trading/**/.expo/

# ── macOS ─────────────────────────────────────────────────────────────────────
.DS_Store
**/.DS_Store
GITIGNORE

echo -e "  ${GREEN}✓ .gitignore created${NC}"

# ── Step 4: Initialize git repo ───────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/5] Initializing git repository…${NC}"

cd "$REPO_ROOT"

if [ ! -d ".git" ]; then
  git init
  git branch -M main
  echo -e "  ${GREEN}✓ Git initialized${NC}"
else
  echo -e "  Git already initialized — updating…"
fi

# Set identity if not already configured
if [ -z "$(git config user.email)" ]; then
  git config user.email "samspisheh@gmail.com"
  git config user.name  "Sam Spisheh"
fi

# Set remote
git remote remove origin 2>/dev/null || true
REMOTE_URL="https://spisheh1:${GITHUB_TOKEN}@github.com/spisheh1/my-website.git"
git remote add origin "$REMOTE_URL"

# ── Step 5: Initial commit and push ───────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/5] Committing and pushing to GitHub…${NC}"

git add "option-trading/"

# Check if there's anything to commit
if git diff --staged --quiet; then
  echo -e "  Nothing new to commit — everything is up to date."
else
  COMMIT_MSG="Initial commit — Options Trader dashboard ($(date '+%Y-%m-%d'))"
  git commit -m "$COMMIT_MSG"
  echo -e "  ${GREEN}✓ Committed${NC}"
fi

# Pull first in case the remote already has commits
git pull origin main --allow-unrelated-histories --no-edit 2>/dev/null || true

# Push
echo -e "  Pushing to GitHub…"
if git push -u origin main 2>&1; then
  echo -e "  ${GREEN}✓ Pushed successfully${NC}"
  PUSH_OK=true
else
  echo -e "  ${RED}✗ Push failed — check your token has 'repo' permission${NC}"
  PUSH_OK=false
fi

# ── Result ─────────────────────────────────────────────────────────────────────
echo ""
if [ "$PUSH_OK" = true ]; then
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  ✓ GitHub sync set up successfully!${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "  Your code is now at:"
  echo -e "  ${CYAN}https://github.com/spisheh1/my-website/tree/main/option-trading${NC}"
  echo ""
  echo -e "  From now on, ${BOLD}every deploy automatically pushes to GitHub${NC}."
else
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${RED}  ✗ Setup incomplete — push failed${NC}"
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "  Try again and make sure your token has the 'repo' scope."
fi

echo ""
echo "  Press any key to close…"
read -rn 1
