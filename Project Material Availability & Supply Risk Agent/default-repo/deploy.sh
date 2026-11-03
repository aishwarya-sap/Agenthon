#!/usr/bin/env bash
# deploy.sh — build the MTA archive and deploy both apps to Cloud Foundry.
# Usage: ./deploy.sh
#
# Routes are assigned automatically from your CF domain via mta.yaml's ${default-url} —
# no CF_APP_DOMAIN needed. Prerequisites:
#   • cf CLI            (cf --version)
#   • mbt               (mbt --version)        https://github.com/SAP/cloud-mta-build-tool
#   • MultiApps plugin  (cf install-plugin multiapps)
#   • a live CF session (cf login --sso)

set -euo pipefail

# ── Prerequisite checks ─────────────────────────────────────────────────────────
command -v cf  >/dev/null 2>&1 || { echo "ERROR: cf CLI not found."; exit 1; }
command -v mbt >/dev/null 2>&1 || { echo "ERROR: mbt not found. Install the Cloud MTA Build Tool."; exit 1; }

if ! cf plugins | grep -qi multiapps; then
  echo "ERROR: MultiApps plugin missing. Run: cf install-plugin multiapps"
  exit 1
fi

# `cf target` prints a CACHED org/space even when the token is expired — hit the API to
# confirm the session is actually live.
if ! cf services >/dev/null 2>&1; then
  echo "ERROR: No live CF session (token missing/expired). Run: cf login --sso"
  exit 1
fi

echo ""
cf target
echo ""
read -rp "Continue with build + deploy to the target above? (y/N): " CONFIRM
[[ "${CONFIRM:-n}" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# ── Build the MTA archive ───────────────────────────────────────────────────────
echo ""
echo "Building MTA archive (mbt build)..."
mbt build

# ── Deploy ──────────────────────────────────────────────────────────────────────
echo ""
echo "Deploying mta_archives/*.mtar ..."
cf deploy mta_archives/*.mtar --strategy rolling

echo ""
echo "Done. Apps deployed:"
cf apps | grep -E "agent-starter-kit" || true
