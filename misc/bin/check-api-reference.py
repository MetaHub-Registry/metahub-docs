#!/usr/bin/env python3
"""Check docs/api.md against the routes the API router serves.

Docs -> router only: every path in a table must exist in the router, with the
same method and the same path-parameter names (except under /v2/, where a
documented <name> stands for one to five repo segments and is compared by
structure).

Usage:
  misc/bin/check-api-reference.py [--router PATH] [--docs PATH]
  METAHUB_API_ROUTER=../metahub-api/pkg/api/v1/router/router.go ...
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROUTE_CALL = re.compile(
    r"\b(?:router|r)\.(Get|Post|Put|Patch|Delete|Head|Options)\(\s*"
    r'(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))\s*,'
)
ROUTE_GROUP = re.compile(r'\brouter\.Route\(\s*"([^"]+)"')
CONST_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"([^\"]+)\"\s*$")
DOC_ROW = re.compile(r"^\|\s*([A-Z][A-Z, ]*?)\s*\|\s*`(/[^`]*)`")
PARAM = re.compile(r"\{([^}]+)\}|<([^>]+)>")


def router_routes(path: Path) -> set[tuple[str, tuple[str, ...]]]:
    consts: dict[str, str] = {}
    for line in path.read_text().splitlines():
        m = CONST_LINE.match(line)
        if m:
            consts[m.group(1)] = m.group(2)

    stack: list[str] = []
    routes: set[tuple[str, tuple[str, ...]]] = set()
    for line in path.read_text().splitlines():
        group = ROUTE_GROUP.search(line)
        if group:
            stack.append(group.group(1))
        call = ROUTE_CALL.search(line)
        if call:
            method, literal, name = call.groups()
            raw = literal if literal is not None else consts.get(name)
            if raw is None:
                continue
            prefix = "".join(stack)
            full = (prefix + raw).rstrip("/") or "/"
            routes.add((method.upper(), tuple(segment(full))))
        if re.match(r"^\s*\}\)\s*$", line) and stack:
            stack.pop()
    return routes


def segment(path: str) -> tuple[str, ...]:
    parts: list[str] = []
    for part in path.strip("/").split("/"):
        if not part:
            continue
        m = PARAM.fullmatch(part)
        parts.append(":" + (m.group(1) or m.group(2)) if m else part)
    return tuple(parts)


def docs_routes(path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in path.read_text().splitlines():
        m = DOC_ROW.match(line)
        if not m:
            continue
        methods = [x.strip() for x in m.group(1).split(",") if x.strip()]
        for method in methods:
            out.append((method, m.group(2)))
    return out


def matches(method: str, doc_path: str, routes) -> bool:
    """Compare one documented path against the router.

    /v2/ documents <name> for one to five repo segments, so expand it and
    compare structure only. /api/v1 compares parameter names too.
    """
    parts = doc_path.strip("/").split("/")
    if parts and parts[0] == "v2":
        for n in range(1, 6):
            expanded: list[str] = []
            for part in parts:
                if not part:
                    continue
                if part == "<name>":
                    expanded.extend([":*"] * n)
                else:
                    m = PARAM.fullmatch(part)
                    expanded.append(":*" if m else part)
            for rmethod, rpath in routes:
                if rmethod != method or len(rpath) != len(expanded):
                    continue
                if all(rp.startswith(":") or rp == dp for rp, dp in zip(rpath, expanded)):
                    return True
        return False

    normalized: list[str] = []
    for part in parts:
        if not part:
            continue
        m = PARAM.fullmatch(part)
        normalized.append(":" + (m.group(1) or m.group(2)) if m else part)
    return (method, tuple(normalized)) in routes


def main() -> int:
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    root = here.parent.parent
    default_router = os.environ.get(
        "METAHUB_API_ROUTER",
        str(root.parent / "metahub-api/pkg/api/v1/router/router.go"),
    )
    ap.add_argument("--router", default=default_router)
    ap.add_argument("--docs", default=str(root / "docs/api.md"))
    args = ap.parse_args()

    router_path = Path(args.router)
    docs_path = Path(args.docs)
    for p in (router_path, docs_path):
        if not p.is_file():
            print(f"error: missing {p}", file=sys.stderr)
            return 2

    routes = router_routes(router_path)
    bad = [entry for entry in docs_routes(docs_path) if not matches(*entry, routes)]

    if bad:
        print(f"FAIL: {len(bad)} documented route(s) are not served:", file=sys.stderr)
        for method, path in bad:
            print(f"  {method:6} {path}", file=sys.stderr)
        return 1

    print(f"ok: {len(docs_routes(docs_path))} documented routes match the router")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
