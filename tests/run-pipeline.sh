#!/usr/bin/env bash
# End-to-end pipeline run against synthetic fixtures: merge -> build -> smoke.
# Proves the config-driven pipeline works without touching any real data.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cp "$REPO"/pipeline/*.py "$REPO"/pipeline/tracker_template.html "$WORK/"
cp "$REPO"/tests/fixtures/* "$WORK/"

cd "$WORK"
python3 merge.py
python3 build_page.py "2026-01-01T00:00:00+00:00"
node "$REPO/scripts/smoke-page.mjs" "$WORK/pr-control.html"

# The built page must carry the placeholder org and nothing real.
grep -q '"org":"your-org"' pr-control.html || { echo "✖ meta.org missing from the built page"; exit 1; }
echo "✔ pipeline end-to-end on fixtures"
