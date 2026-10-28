#!/usr/bin/env bash
# deploy.sh — push Material Risk Agent + Chat UI to Cloud Foundry
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
echo "Deploying Material Risk Agent to: $CF_APP_DOMAIN"

# ── CF login check ────────────────────────────────────────────────────────────
if ! cf target &>/dev/null; then
  echo ""
  echo "ERROR: Not logged in to CF."
  echo "Run: cf login -a https://api.cf.${CF_APP_DOMAIN#cfapps.}"
  exit 1
fi

echo ""
cf target

echo ""
echo "Agent URL (after deploy):  https://material-risk-agent.${CF_APP_DOMAIN}/"
echo "UI URL (after deploy):     https://material-risk-ui.${CF_APP_DOMAIN}/"
echo ""
read -rp "Continue? (y/N): " CONFIRM
[[ "${CONFIRM:-n}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# ── Push ──────────────────────────────────────────────────────────────────────
echo ""
echo "Running: cf push -f manifest.yml"
cf push -f manifest.yml

echo ""
echo "Deployed. Checking app status..."
cf apps | grep -E "material-risk"

echo ""
echo "Agent card:  curl https://material-risk-agent.${CF_APP_DOMAIN}/.well-known/agent.json"
echo "UI:          https://material-risk-ui.${CF_APP_DOMAIN}/"
