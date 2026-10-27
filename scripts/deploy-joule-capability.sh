#!/usr/bin/env bash
# deploy-joule-capability.sh — Deploy the Joule pro-code capability via the Joule CLI.
#
# Pre-requisites (complete these first — see docs/INTEGRATION_GUIDE.md Steps 8–11):
#   1. CF agent is deployed + IAS env vars set (run scripts/setup-ias-env.sh first)
#   2. BTP Destination "MATERIAL_RISK_AGENT" exists with Authentication=OAuth2JWTBearer
#   3. IAS app2app trust wired (A2A Proxy IAS app → Custom-Agent IAS app)
#   4. Joule CLI installed: npm install -g @sap/joule-cli  (or from SAP Tooling page)
#
# Usage:
#   BTP_SUBACCOUNT_ID=<uuid> ./scripts/deploy-joule-capability.sh
#   OR run interactively:
#   ./scripts/deploy-joule-capability.sh
#
# What this does:
#   1. Validates the agent card is reachable (sanity check before CLI call)
#   2. Runs: joule capability deploy --path ./joule/da.sapdas.yaml --subaccount <id>
#   3. Prints a test prompt to verify Joule intent matching
#
# After running: open the Joule panel and type:
#   "What materials are at risk for project P-ALPHA-01?"

set -euo pipefail

CAPABILITY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SAPDAS_YAML="$CAPABILITY_DIR/joule/da.sapdas.yaml"

# ---------------------------------------------------------------------------
# Collect BTP subaccount ID
# ---------------------------------------------------------------------------
if [[ -z "${BTP_SUBACCOUNT_ID:-}" ]]; then
  read -rp "BTP Subaccount ID (GUID, from BTP Cockpit → Subaccount Overview): " BTP_SUBACCOUNT_ID
fi

# ---------------------------------------------------------------------------
# Sanity check: agent card reachable?
# ---------------------------------------------------------------------------
if [[ -n "${CF_APP_DOMAIN:-}" ]]; then
  AGENT_URL="https://material-risk-agent.${CF_APP_DOMAIN}"
  echo "Checking agent card at ${AGENT_URL}/.well-known/agent.json ..."
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${AGENT_URL}/.well-known/agent.json" 2>/dev/null || echo "000")
  if [[ "$STATUS" == "200" ]]; then
    echo "  Agent card: HTTP $STATUS ✓"
  else
    echo "  WARNING: Agent card returned HTTP $STATUS"
    echo "  Make sure the agent is deployed (./deploy.sh) before registering the Joule capability."
    read -rp "  Continue anyway? [y/N] " cont
    [[ "${cont,,}" == "y" ]] || { echo "Aborted."; exit 1; }
  fi
fi

# ---------------------------------------------------------------------------
# Deploy the capability
# ---------------------------------------------------------------------------
echo ""
echo "=== Deploying Joule capability ==="
echo "  YAML:         $SAPDAS_YAML"
echo "  Subaccount:   $BTP_SUBACCOUNT_ID"
echo ""

if ! command -v joule &>/dev/null; then
  echo "ERROR: Joule CLI not found. Install with:"
  echo "  npm install -g @sap/joule-cli"
  echo "  OR download from https://tools.hana.ondemand.com/"
  exit 1
fi

joule capability deploy \
  --path "$SAPDAS_YAML" \
  --subaccount "$BTP_SUBACCOUNT_ID"

echo ""
echo "=== Capability deployed! Test with: ==="
echo "  Open Joule panel and type:"
echo "    'What materials are at risk for project P-ALPHA-01?'"
echo ""
echo "  Expected: Joule returns the 7-section Material Risk report."
echo "  If Joule says 'no capability matched': broaden the scenario description"
echo "  in joule/material_risk_capability/scenarios/material_risk_scenario.yaml"
