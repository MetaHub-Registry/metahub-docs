#!/usr/bin/env bash
# Render every .excalidraw source under docs/assets/diagrams/ to a sibling PNG.
#
# Usage:
#   misc/diagrams/render-all.sh            # render all diagrams
#   misc/diagrams/render-all.sh foo bar    # render only foo.excalidraw, bar.excalidraw
#
# Requires `uv` (https://docs.astral.sh/uv/). First run installs Playwright +
# Chromium into a local .venv next to this script.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/../.." && pwd)"
DIAGRAM_DIR="${REPO_ROOT}/docs/assets/diagrams"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: 'uv' is required (https://docs.astral.sh/uv/)." >&2
  exit 1
fi

cd "${HERE}"

# One-time / idempotent environment setup.
uv sync --quiet
if ! uv run python -c "import playwright" >/dev/null 2>&1; then
  echo "ERROR: playwright import failed after uv sync." >&2
  exit 1
fi
# Ensure the Chromium browser is present (no-op if already installed).
uv run playwright install chromium >/dev/null

# Collect targets.
targets=()
if [ "$#" -gt 0 ]; then
  for name in "$@"; do
    targets+=("${DIAGRAM_DIR}/${name%.excalidraw}.excalidraw")
  done
else
  while IFS= read -r f; do targets+=("$f"); done \
    < <(find "${DIAGRAM_DIR}" -maxdepth 1 -name '*.excalidraw' | sort)
fi

if [ "${#targets[@]}" -eq 0 ]; then
  echo "No .excalidraw sources found in ${DIAGRAM_DIR}" >&2
  exit 0
fi

for src in "${targets[@]}"; do
  if [ ! -f "${src}" ]; then
    echo "SKIP (missing): ${src}" >&2
    continue
  fi
  echo ">> rendering $(basename "${src}")"
  uv run python render_excalidraw.py "${src}"
done

echo "Done. PNGs written next to their .excalidraw sources in ${DIAGRAM_DIR}"
