#!/usr/bin/env bash
# Print the Python third-party notices in Markdown. CI regenerates this file
# and fails when the committed copy differs. Run inside the docs virtualenv.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${ROOT}"

cat <<'HEADER'
# Third-party notices

Generated from the docs virtualenv with `pip-licenses`. Do not edit by hand:
run `.github/scripts/third-party-notices.sh > THIRD_PARTY_NOTICES.md`.

HEADER

pip-licenses --format=markdown
