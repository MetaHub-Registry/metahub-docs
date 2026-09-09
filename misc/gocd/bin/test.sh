#!/bin/sh
set -e
docker build --target build -t metahub-docs-test .
docker run --rm metahub-docs-test mkdocs build --strict
