# Context: metahub-docs

> This file helps AI agents understand the repo quickly.

## Session: readd-pull-through-cache (2026-09-14) — branch `8-readd-pull-through-cache`

Commit `816c026`: added the **Pull-Through Cache** documentation page
(config reference for the `registries[].pull_through` block — `enabled`,
`client_redirect`, `cache`, `refresh_interval`, flat `user`/`password`
credentials — plus delivery semantics: proxy-by-default for credentialed
registries, `client_redirect: true` as the client-side-login opt-in) and
wired it into the nav and landing page.

Follow-ups for future sessions:
- Document the GoCD `pull-through-test` pipeline stages (anon / HarborPrivate
  / GitLabPrivate) and how to rotate the upstream credentials in the flux
  SOPS secret (`SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt` prefix on
  macOS).
- The `client_redirect: true` docs note should mention that clients need
  `docker login <upstream>` for blob delivery (manifests always resolve via
  metahub's server-side credentials).

## Session close — 2026-10-20

- Profile-resolution page added; internal hosts and private IPs replaced with
  `*.example.com` and IANA documentation ranges.
- Trust model, `/api/v1` reference, and the profile extension v1 specification
  added and wired into the nav; `mkdocs build --strict` passes.
- Merged current `main` (licence/community).

## 2026-10-23 — open-source-metahub

- Added the public CI fast lane (`mkdocs --strict`, licence/notices, DCO,
  gitleaks, telemetry) and the `fast` aggregator.
- No content changes beyond the API examples touched for the natural-key
  change.
