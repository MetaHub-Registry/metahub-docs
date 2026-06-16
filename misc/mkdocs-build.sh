#!/usr/bin/env sh
# Build (or serve) the docs with the version baked into the footer.
#
# Usage:
#   misc/mkdocs-build.sh            # mkdocs build --strict
#   misc/mkdocs-build.sh serve      # mkdocs serve (live preview)
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
VERSION="$("${HERE}/version.sh")"

export MKDOCS_VERSION="${VERSION}"
export MKDOCS_COPYRIGHT="MetaHub Docs · ${VERSION}"

echo "docs version: ${VERSION}"

if [ "${1:-}" = "serve" ]; then
  exec mkdocs serve
fi

exec mkdocs build --strict
