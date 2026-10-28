#!/usr/bin/env bash
# deploy.sh — push both apps to Cloud Foundry
# Usage: ./deploy.sh
# Or:    CF_APP_DOMAIN=cfapps.<region>.hana.ondemand.com ./deploy.sh

set -euo pipefail

# ── CF domain ─────────────────────────────────────────────────────────────────
if [[ -z "${CF_APP_DOMAIN:-}" ]]; then
  echo ""
  echo "Enter your CF app domain (e.g. cfapps.<region>.hana.ondemand.com):"
  echo ""
  read -rp "CF_APP_DOMAIN: " CF_APP_DOMAIN
fi

export CF_APP_DOMAIN

echo ""
echo "Deploying to domain: $CF_APP_DOMAIN"
echo ""

# ── CF target check ───────────────────────────────────────────────────────────
if ! cf target &>/dev/null; then
  echo "ERROR: Not logged in to CF. Run: cf login -a https://api.cf.<region>.hana.ondemand.com"
  exit 1
fi

cf target

echo ""
read -rp "Continue with deployment? (y/N): " CONFIRM
[[ "${CONFIRM:-n}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# ── Push ──────────────────────────────────────────────────────────────────────
echo ""
echo "Pushing agent and UI..."
cf push -f manifest.yml

echo ""
echo "Done. Apps deployed:"
cf apps | grep -E "agent-starter-kit"
