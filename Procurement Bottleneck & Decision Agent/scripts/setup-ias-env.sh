#!/usr/bin/env bash
# setup-ias-env.sh — Configure IAS Principal Propagation env vars on the deployed CF app.
#
# Run this ONCE after Step 9 (IAS app creation) and Step 10 (BTP Destination) from
# docs/INTEGRATION_GUIDE.md are complete. You'll need the IAS tenant URL, the
# Custom-Agent IAS app's Client ID, and (optionally) the API grant name.
#
# Usage:
#   IAS_TENANT=<yourtenantid>.accounts.ondemand.com ./scripts/setup-ias-env.sh
#   OR run interactively (prompts for values):
#   ./scripts/setup-ias-env.sh
#
# What this does:
#   1. Sets AGENT_AUTH_MODE=ias    → switches from mock to IAS validation
#   2. Sets IAS_JWKS_URI            → where to fetch the IAS public keys
#   3. Sets IAS_ISSUER              → the IAS tenant URL (iss claim in the JWT)
#   4. Sets IAS_AUDIENCE            → the Custom-Agent IAS app Client ID
#   5. Sets IAS_REQUIRED_API        → API name exposed on the Custom-Agent app
#   6. Sets ENABLE_WHOAMI=1         → exposes /whoami for identity-chain debugging
#   7. Calls cf restage to pick up the new env vars
#
# After running: test with:
#   curl -H "Authorization: Bearer <ias-token>" \
#     https://procurement-bottleneck-agent.<CF_DOMAIN>/whoami | python3 -m json.tool

set -euo pipefail

APP_NAME="${CF_APP_NAME:-procurement-bottleneck-agent}"

# ---------------------------------------------------------------------------
# Collect IAS tenant details
# ---------------------------------------------------------------------------
if [[ -z "${IAS_TENANT:-}" ]]; then
  read -rp "IAS tenant hostname (e.g. yourtenantid.accounts.ondemand.com): " IAS_TENANT
fi
IAS_TENANT="${IAS_TENANT#https://}"   # strip leading https:// if pasted

if [[ -z "${IAS_CLIENT_ID:-}" ]]; then
  read -rp "Custom-Agent IAS app Client ID (from IAS Admin → Applications): " IAS_CLIENT_ID
fi

IAS_API_GRANT="${IAS_API_GRANT:-a2a_custom_agent_app_api}"

echo ""
echo "=== Setting env vars on CF app: $APP_NAME ==="
echo "  IAS tenant:  $IAS_TENANT"
echo "  Client ID:   $IAS_CLIENT_ID"
echo "  API grant:   $IAS_API_GRANT"
echo ""

read -rp "Proceed? [y/N] " confirm
[[ "${confirm,,}" == "y" ]] || { echo "Aborted."; exit 0; }

# ---------------------------------------------------------------------------
# Apply env vars
# ---------------------------------------------------------------------------
cf set-env "$APP_NAME" AGENT_AUTH_MODE      "ias"
cf set-env "$APP_NAME" IAS_JWKS_URI         "https://${IAS_TENANT}/oauth2/certs"
cf set-env "$APP_NAME" IAS_ISSUER           "https://${IAS_TENANT}"
cf set-env "$APP_NAME" IAS_AUDIENCE         "$IAS_CLIENT_ID"
cf set-env "$APP_NAME" IAS_REQUIRED_API     "$IAS_API_GRANT"
cf set-env "$APP_NAME" ENABLE_WHOAMI        "1"

echo ""
echo "=== Restaging $APP_NAME to apply new env vars ==="
cf restage "$APP_NAME"

echo ""
echo "=== Done! Verify identity chain: ==="
echo "  curl -H 'Authorization: Bearer <your-ias-token>' \\"
echo "    https://$(cf app "$APP_NAME" | grep route | awk '{print $2}')/whoami"
