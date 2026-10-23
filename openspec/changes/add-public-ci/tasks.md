# Tasks — public CI for metahub-docs

## 1. Fast lane

- [x] 1.1 Add `.github/workflows/ci.yml` with `push`/`pull_request` triggers,
      `permissions: contents: read`, concurrency cancellation and a `fast`
      aggregator.
- [x] 1.2 Add the build, static-analysis, lint and container-free test jobs.
- [x] 1.3 Add gitleaks (pinned CLI, committed config), DCO and the outbound-host
      allowlist. Add the pip licence allowlist and generated
      `THIRD_PARTY_NOTICES.md`.
- [x] 1.4 Add `.github/dependabot.yml`.

## 2. Integration lane

- [x] 2.1 No container-backed tests; no integration workflow is needed.

## 3. Follow-ups

- [ ] 3.1 Keep the strict MkDocs build and the licence allowlist green as
      the docs dependencies move.
- [ ] 3.2 Run the fast lane from a fork pull request before the visibility flip
      and record the run URL here.
