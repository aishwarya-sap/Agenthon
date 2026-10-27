#!/usr/bin/env bash
# Regenerate the requirements.txt lock from pyproject.toml using uv.
# The CF python_buildpack installs from requirements.txt, so we keep it committed as
# the build-time lock; pyproject.toml is the source of truth for dependency ranges.
#
# Usage:  ./freeze-deps.sh
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

# Resolve runtime deps from pyproject into a pinned requirements.txt (buildpack lock).
uv pip compile pyproject.toml -o requirements.txt
echo "Wrote requirements.txt from pyproject.toml"
