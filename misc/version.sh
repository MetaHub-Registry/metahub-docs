#!/usr/bin/env sh
# Resolve the docs version using the same tag logic as the GoCD pipelines:
#   - on an exact git tag  -> the tag (e.g. v1.2.0)
#   - otherwise            -> main:<short-sha>
#
# Prints the version to stdout. Safe to run outside a git checkout (CI build
# context may strip .git); falls back to "dev".
set -eu

GIT_TAG="$(git describe --tags --exact-match 2>/dev/null || true)"
if [ -n "${GIT_TAG}" ]; then
  echo "${GIT_TAG}"
  exit 0
fi

SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
if [ -n "${SHA}" ]; then
  echo "main:${SHA}"
  exit 0
fi

echo "dev"
