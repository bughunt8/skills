#!/usr/bin/env bash
# Evidence runner for the graph-motion acceptance work.
#
# Every run writes into its own directory, keyed by the commit under test and a
# UTC stamp, so no earlier report is ever overwritten:
#
#   $EVIDENCE_ROOT/<short-sha>[-dirty]/<utc-stamp>-<suite|proofs>/
#
# Usage:
#   scripts/run-motion-evidence.sh suite     # full Playwright suite, one worker
#   scripts/run-motion-evidence.sh proofs    # planted-defect proof runner
#
# The port and worker count are fixed on purpose: the mobile commit long task is
# load-sensitive, so results are only comparable at --workers=1 on the isolated
# port agreed with the implementation worker.
set -euo pipefail

MODE="${1:?usage: run-motion-evidence.sh suite|proofs}"
SITE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$(cd "$SITE_DIR/.." && pwd)"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-/home/user/workspace/work/motion-evidence}"
export SITE_TEST_PORT="${SITE_TEST_PORT:-8241}"
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="${PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH:-/home/user/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome}"

SHA="$(git -C "$REPO_DIR" rev-parse HEAD)"
SHORT="$(git -C "$REPO_DIR" rev-parse --short HEAD)"
if ! git -C "$REPO_DIR" diff --quiet -- site/app.js site/styles.css site/index.html; then
  SHORT="${SHORT}-dirty"
fi
RUN_DIR="$EVIDENCE_ROOT/$SHORT/$(date -u +%Y%m%dT%H%M%SZ)-$MODE"
mkdir -p "$RUN_DIR"

# Hash exactly what is under test, before the run, into the run directory.
{
  echo "{"
  echo "  \"commitUnderTest\": \"$SHA\","
  echo "  \"uiDirty\": $(git -C "$REPO_DIR" diff --quiet -- site/app.js site/styles.css site/index.html && echo false || echo true),"
  echo "  \"port\": $SITE_TEST_PORT,"
  echo "  \"workers\": 1,"
  echo "  \"mode\": \"$MODE\","
  echo "  \"startedAt\": \"$(date -uIs)\","
  echo "  \"sha256\": {"
  first=1
  for f in app.js styles.css index.html data.js MOTION.md UI_NAVIGATION.md \
           tests/graph-motion.spec.js tests/resilience.spec.js \
           scripts/motion-test-helpers.mjs scripts/prove-motion-defects.mjs \
           scripts/workspace-test-helpers.mjs; do
    [ $first -eq 1 ] || echo ","
    first=0
    printf '    "%s": "%s"' "$f" "$(sha256sum "$SITE_DIR/$f" | cut -d' ' -f1)"
  done
  echo
  echo "  }"
  echo "}"
} > "$RUN_DIR/run-context.json"

cd "$SITE_DIR"
if [ "$MODE" = "suite" ]; then
  WORKSPACE_EVIDENCE_DIR="$RUN_DIR/playwright" \
  PLAYWRIGHT_JSON_OUTPUT_FILE="$RUN_DIR/full-suite.json" \
    npx playwright test --workers=1 --retries=1 --reporter=list,json \
    > "$RUN_DIR/full-suite.log" 2>&1 || true
  tail -5 "$RUN_DIR/full-suite.log"
else
  WORKSPACE_EVIDENCE_DIR="$RUN_DIR" \
    node scripts/prove-motion-defects.mjs > "$RUN_DIR/prove-motion-run.log" 2>&1 || true
  tail -5 "$RUN_DIR/prove-motion-run.log"
fi
echo "evidence: $RUN_DIR"
