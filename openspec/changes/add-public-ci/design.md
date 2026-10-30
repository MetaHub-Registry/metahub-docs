# Design — public CI for metahub-docs

## Stack and boundary

MkDocs Material (Python).

Fast checks:

- `pip install -r requirements.txt`
- `misc/mkdocs-build.sh` (`mkdocs build --strict`)
- `pip-licenses` allowlist and generated `THIRD_PARTY_NOTICES.md`
- `gitleaks` with the committed `.gitleaks.toml`
- DCO trailer check
- outbound-host allowlist

Container-backed checks: There are no container-backed tests.

CI pins Python 3.12 while the local toolchain may be newer; the build is the same strict MkDocs invocation used by `task check`.

## Decisions

### Self-contained, fork-safe workflows

The workflows live in this repository. A cross-repository reusable workflow
would need either a public `.github` repository before the launch gate or
private access that a fork does not receive. Every PR-triggered workflow is
therefore self-contained, declares `permissions: contents: read`, pins
third-party actions by SHA and references no secret.

### One aggregator

`fast` depends on every fast job and fails when any of them fails or is
cancelled. Marking only `fast` as a required check at the visibility flip keeps
the branch-protection configuration stable as checks are added.

### No release-only lane

The MkDocs build and the licence check are container-free and run on every
pull request. There is no `integration.yml` and no check is deferred to a
release tag.

### Dependencies and licences

`pip-licenses --partial-match` checks the docs virtualenv against the
allowlist and the generated notices file is compared for drift.

### Outbound hosts

Non-test source may reference only hosts on `.github/outbound-allowlist.txt`.
A new host fails the job and must be added deliberately in review. This is a
review gate, not a network sandbox.

## Risks

| Risk | Mitigation |
|---|---|
| A workflow needs a secret when run from a fork | it belongs in the integration lane or is dropped |
| Action supply chain | every action is pinned to a full commit SHA |
| Dependency advisories | Dependabot opens weekly pip PRs; the strict build and `pip-licenses` remain the blocking gates |
