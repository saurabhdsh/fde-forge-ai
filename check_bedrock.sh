#!/usr/bin/env bash
# One-shot Bedrock access check (Mac / TCS — uses ~/.aws or env keys)
#
# Usage:
#   chmod +x check_bedrock.sh
#   ./check_bedrock.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}==>${NC} FDE Forge AI — Bedrock access check"
echo -e "${BLUE}==>${NC} Repo: $ROOT"

if [[ ! -f "$ROOT/.env" ]]; then
  echo -e "${RED}✖${NC} No .env found. Run ./setup.sh first (FORCE_MODE=native on TCS Mac)."
  exit 1
fi

if [[ ! -f "$ROOT/apps/api/.venv/bin/activate" ]]; then
  echo -e "${RED}✖${NC} Python venv missing. Run: FORCE_MODE=native ./setup.sh"
  exit 1
fi

# Load app env (quoted values OK)
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a

# shellcheck disable=SC1091
source "$ROOT/apps/api/.venv/bin/activate"
export PYTHONPATH="$ROOT/apps/api:$ROOT"

echo -e "${BLUE}==>${NC} Running python -m scripts.check_bedrock ..."
echo ""

if python -m scripts.check_bedrock; then
  echo ""
  echo -e "${GREEN}✔${NC} Bedrock is reachable with your AWS credentials."
  echo "  You can generate domain courses in the UI."
  echo "  Optional API check (while logged in): GET /api/v1/ai/bedrock/check"
  exit 0
fi

echo ""
echo -e "${RED}✖${NC} Bedrock check failed."
echo -e "${YELLOW}!${NC} Fix credentials, then retry:"
echo "    aws configure          # region us-east-1"
echo "    aws sts get-caller-identity"
echo "    ./check_bedrock.sh"
echo "  IAM needs: bedrock:InvokeModel (and model access in us-east-1)"
exit 1
