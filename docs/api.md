# API reference — `/api/v1`

> **Status:** describes the 1.0 surface. The natural-key identifier migration
> lands before 1.0; numeric `id` fields in some responses are transitional and
> will become stable string keys.

## Base URL and versioning

All management endpoints live under `/api/v1`. The OCI distribution endpoints
live under `/v2/`.

Changes within a version are additive. A breaking change ships as `/api/v2`
alongside v1.

## Authentication

### OCI token service — `GET /auth`

Docker and containerd call this after receiving a `401` from `/v2/`. The
username may carry a profile suffix:

```bash
curl -u 'alice/zen2:password' 'https://registry.example.com/auth?account=alice/zen2'
```

```json
{ "token": "…" }
```

- `account` takes precedence over the Basic-auth username when both are sent.
- `user/profile` selects the profile; `user` alone falls back to `generic` or
  to the inventory lookup.
- Anonymous requests receive a generic token.

### Management API

Use the bearer token from the OIDC login flow, or from
`POST /api/v1/godmode/login` when god-mode is enabled:

```bash
curl -H "Authorization: Bearer $TOKEN" https://registry.example.com/api/v1/profiles
```

`/api/v1/protected/projects/*` additionally requires the **admin** role. Other
protected endpoints require any authenticated user.

## OCI distribution API

| Method | Path | Purpose |
|---|---|---|
| GET | `/v2/` | API version check / auth challenge |
| GET, HEAD | `/v2/<name>/manifests/<reference>` | Fetch a manifest by tag or digest |
| PUT | `/v2/<name>/manifests/<reference>` | Push a manifest |
| DELETE | `/v2/<name>/manifests/<reference>` | Delete a manifest |
| GET, HEAD | `/v2/<name>/blobs/<digest>` | Fetch a blob |
| POST | `/v2/<name>/blobs/uploads/` | Start a blob upload |
| PATCH, PUT | `/v2/<name>/blobs/uploads/<uuid>` | Upload blob content |
| GET | `/v2/<name>/tags/list` | List tags |
| GET | `/v2/<name>/referrers/<digest>` | List referrers (ORAS artefacts) |

`<name>` may contain up to four path segments, so deep upstream repositories
work without a separate route.

Read and write authorization is enforced by middleware. Pull authorization and
write-ownership checks are configuration switches; see the operations guide.

## Management API — public

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/collections` | List collections below a repo prefix |
| POST | `/api/v1/collection` | Fetch one collection and its manifests |
| GET | `/api/v1/oras` | List ORAS artefacts |
| GET | `/api/v1/oras/artifact` | Fetch one ORAS artefact |
| GET | `/api/v1/models` | List model definitions |
| GET | `/api/v1/models/<ref>` | Model detail |
| GET | `/api/v1/models/<ref>/compositions` | Model compositions per profile |
| GET | `/api/v1/models/<org>/<name>` | Org-qualified model detail |
| GET | `/api/v1/manifest/blob-content` | Stream a config blob as text |
| GET | `/api/v1/runtimes` | Runtime registry |
| GET | `/api/v1/profiles` | List profiles |
| GET | `/api/v1/profiles/<label>` | Profile detail, rules, manipulations |
| GET | `/api/v1/registries` | Configured upstream registries |
| GET | `/api/v1/version` | API and core library versions |
| GET | `/api/v1/auth/config` | Authentication mode discovery |
| GET | `/api/v1/login` | OIDC login redirect |
| GET | `/api/v1/callback` | OIDC callback |
| POST | `/api/v1/godmode/login` | JSON login (404 when god-mode is off) |

## Management API — protected

Requires a bearer token.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/protected/logout` | End the session |
| GET | `/api/v1/protected/session` | Current session |
| POST | `/api/v1/protected/registry-token` | Create a registry token |
| GET | `/api/v1/protected/registry-tokens` | List registry tokens |
| DELETE | `/api/v1/protected/registry-tokens/<id>` | Revoke a registry token |
| GET | `/api/v1/protected/user` | Current user |
| GET | `/api/v1/protected/users/<id>` | User by id |
| PUT | `/api/v1/protected/user/secret` | Store a user secret |
| DELETE | `/api/v1/protected/user/secret/<id>` | Delete a user secret |

Admin-only, `/api/v1/protected/projects`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/protected/projects` | Create a project |
| GET | `/api/v1/protected/projects` | List projects |
| GET | `/api/v1/protected/projects/<team>/<project>` | Project detail |
| GET | `/api/v1/protected/projects/<team>/<project>/usage` | Usage |
| PUT | `/api/v1/protected/projects/<team>/<project>/quota` | Set quota |
| PUT | `/api/v1/protected/projects/<team>/<project>/visibility` | Set visibility |
| DELETE | `/api/v1/protected/projects/<team>/<project>` | Delete a project |

## Examples

### List collections

```bash
curl -s -X POST https://registry.example.com/api/v1/collections \
  -H 'Content-Type: application/json' \
  -d '{"repo":"qnib/llama-server","profile":"cpu#zen2"}'
```

```json
{
  "repos": ["qnib", "qnib/llama-server"],
  "bread_crumbs": [],
  "next": [],
  "slug_end": true
}
```

### Fetch one collection

```bash
curl -s -X POST https://registry.example.com/api/v1/collection \
  -H 'Content-Type: application/json' \
  -d '{"repo_name":"qnib/ftest","tag_name":"latest","profile":"cpu#zen2"}'
```

```json
{
  "repos": ["qnib", "qnib/ftest"],
  "bread_crumbs": [],
  "collection": {
    "name": "qnib/ftest",
    "tag": "latest",
    "manifests": [
      {
        "digest": "sha256:…",
        "media_type": "application/vnd.oci.image.manifest.v1+json",
        "platform": { "os": "linux", "architecture": "amd64" },
        "size": 1234,
        "profiles": ["cpu#zen2"]
      }
    ]
  }
}
```

`profile` is an optional post-filter. Omit it for the unfiltered collection.

### Profile detail

```bash
curl -s https://registry.example.com/api/v1/profiles/generic
```

```json
{
  "name": "generic",
  "tag": "latest",
  "label": "generic",
  "rules": [
    { "type": "os", "op": "eq", "key": "linux", "value": "true" }
  ],
  "collection_count": 12,
  "manifest_count": 34,
  "manipulations": []
}
```

### Create a project

```bash
curl -s -X POST https://registry.example.com/api/v1/protected/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"team_slug":"acme","project_slug":"ml","quota_bytes":10737418240,"visibility":"private"}'
```

```json
{
  "team_slug": "acme",
  "project_slug": "ml",
  "namespace": "acme/ml",
  "quota_bytes": 10737418240,
  "usage_bytes": 0,
  "visibility": "private"
}
```

## Errors

The management API returns a JSON object with an `error` field:

```json
{ "error": "profile not found" }
```

The OCI endpoints follow the distribution specification:
`{"errors":[{"code":"…","message":"…"}]}` with the matching status code.

## Inventory service

Profile resolution by client IP lives in **metahub-admin-ui**, not in
metahub-api:

```bash
curl 'https://inventory.example.com/api/v1/resolve?ip=192.0.2.7'
```

```json
{ "ip": "192.0.2.7", "profile": "cpu#zen2", "hostname": "node1.example.com", "source": "hostname:1" }
```

A `404` with `{}` means no match; consumers fail open to `generic`.
