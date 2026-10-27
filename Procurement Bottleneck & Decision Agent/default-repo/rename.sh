#!/usr/bin/env bash
# rename.sh — Replace all occurrences of the starter-kit placeholder name with your agent name.
#
# Usage:
#   chmod +x rename.sh
#   ./rename.sh <your-agent-name>
#
# Example:
#   ./rename.sh material-risk-agent
#
# What it touches:
#   - All YAML, JSON, Python, and text files inside assets/
#   - Renames the assets/agent-starter-kit/ folder itself
#   - Does NOT touch .venv, __pycache__, .git

set -euo pipefail

OLD="agent-starter-kit"          # kebab-case placeholder (files, folders, CF/XSUAA names)
OLD_US="agent_starter_kit"       # snake_case placeholder (Joule capability name — snake-case required)
NEW="${1:-}"

if [[ -z "$NEW" ]]; then
  echo "Usage: ./rename.sh <your-agent-name>   (kebab-case, e.g. material-risk-agent)"
  exit 1
fi

if [[ ! -d "assets/$OLD" ]]; then
  echo "Error: assets/$OLD not found. Run from the default-repo root."
  exit 1
fi

# Joule capability names must be snake_case, so derive the underscore variant of the new name.
NEW_US="${NEW//-/_}"

echo "Renaming '$OLD' → '$NEW'  (snake-case: '$OLD_US' → '$NEW_US') ..."

# 1. Rename the top-level asset folder first, then work inside it.
mv "assets/$OLD" "assets/$NEW"
ROOT="assets/$NEW"

# 2. Replace both name forms in file contents (snake-case first so it can't be
#    partially clobbered by the kebab-case pass).
find "$ROOT" -type f \
  ! -path '*/.venv/*' \
  ! -path '*/__pycache__/*' \
  ! -name '*.pyc' \
  \( -name '*.py' -o -name '*.yaml' -o -name '*.yml' -o -name '*.json' \
     -o -name '*.md' -o -name '*.txt' -o -name '*.ini' -o -name '*.properties' \
     -o -name 'Procfile' -o -name '.env.example' -o -name '.cfignore' \) \
  -exec sed -i '' -e "s/$OLD_US/$NEW_US/g" -e "s/$OLD/$NEW/g" {} +

# 3. Rename nested files/folders whose NAME carries the placeholder (e.g. the Joule
#    capability bundle joule/agent-starter-kit-capability). -depth = deepest first so a
#    parent is never renamed out from under its children.
find "$ROOT" -depth \
  ! -path '*/.venv/*' ! -path '*/__pycache__/*' \
  \( -name "*$OLD*" -o -name "*$OLD_US*" \) -print0 2>/dev/null |
while IFS= read -r -d '' p; do
  np="$(printf '%s' "$p" | sed -e "s/$OLD_US/$NEW_US/g" -e "s/$OLD/$NEW/g")"
  [[ "$p" != "$np" ]] && mv "$p" "$np"
done

echo "Done. Folder renamed to assets/$NEW"
echo "  • CF / XSUAA / asset names  → $NEW"
echo "  • Joule capability name     → ${NEW_US}_capability"
echo "  • Joule bundle folder       → assets/$NEW/joule/${NEW}-capability"
echo ""
echo "Next: fill in all [TODO] placeholders, then verify:"
echo "  IBD_TESTING=1 pytest assets/$NEW/tests/"
