#!/usr/bin/env bash
# Show what changed in core's Insteon integration between the tag this repo is
# based on (UPSTREAM_BASE) and another core tag. Use it on every Home Assistant
# release to decide whether this integration needs a merge.
#
#   scripts/upstream-diff.sh <core-tag> [base-tag]
#
# Fetches file lists from the GitHub API so added or removed files show up too.
# Also diffs our custom_components/insteon against the new tag, filtered to the
# files upstream touched, so you can see whether a fork change collides.
set -euo pipefail

TAG="${1:?usage: $0 <core-tag> [base-tag]}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${2:-$(cat "$REPO/UPSTREAM_BASE")}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fetch() {  # fetch <tag> <dir>
  local tag="$1" dir="$2" path
  mkdir -p "$dir/api"
  gh api "repos/home-assistant/core/git/trees/$tag?recursive=1" \
    --jq '.tree[] | select(.type=="blob") | select(.path | startswith("homeassistant/components/insteon/")) | .path' \
  | while read -r path; do
      curl -sfL "https://raw.githubusercontent.com/home-assistant/core/$tag/$path" \
        -o "$dir/${path#homeassistant/components/insteon/}"
    done
}

echo "Fetching core $BASE (this repo's base) and $TAG ..."
fetch "$BASE" "$WORK/base"
fetch "$TAG" "$WORK/new"

echo
echo "===== upstream insteon: $BASE -> $TAG ====="
if diff -ru "$WORK/base" "$WORK/new" > "$WORK/upstream.diff"; then
  echo "No changes. Nothing to merge."
else
  diffstat "$WORK/upstream.diff" 2>/dev/null || grep -E '^(diff|Only in)' "$WORK/upstream.diff"
  echo
  cat "$WORK/upstream.diff"
fi

echo
echo "===== requirements / python =====" 
diff <(python3 -c "import json;print('\n'.join(json.load(open('$WORK/base/manifest.json'))['requirements']))") \
     <(python3 -c "import json;print('\n'.join(json.load(open('$WORK/new/manifest.json'))['requirements']))") \
  && echo "requirements unchanged" || true
curl -sfL "https://raw.githubusercontent.com/home-assistant/core/$TAG/pyproject.toml" | grep requires-python

echo
echo "===== this repo vs core $TAG, files upstream touched ====="
touched=$(grep -E '^(diff -ru|Only in)' "$WORK/upstream.diff" 2>/dev/null \
  | sed -E "s#.*$WORK/new/##; s#^Only in $WORK/(base|new)/?(.*): (.*)#\2/\3#; s#^/##; s# .*##" | sort -u || true)
if [ -z "$touched" ]; then echo "(none)"; else
  for f in $touched; do
    echo "--- $f"
    diff -u "$WORK/new/$f" "$REPO/custom_components/insteon/$f" 2>&1 | tail -n +3 || true
  done
fi
