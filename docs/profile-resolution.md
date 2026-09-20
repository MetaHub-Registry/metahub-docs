# Profile Resolution

MetaHub can assign a pull profile based on **where a login comes from** — the
node's identity, not the user's typing. A client that authenticates without a
profile suffix (`docker login -u oci`) receives the profile that belongs to
its IP: seed one inventory entry per GPU island and every headless pull
(SLURM prologs, kubelets, containerd) picks the right manipulations
automatically. An explicit `user/profile` suffix always wins and remains the
per-client override.

```
docker login -u oci            (from 192.168.5.115)
  └─► GET /auth                     metahub-api (token mint)
        clientIP = 192.168.5.115 ──► GET /api/v1/resolve?ip=…   metahub-admin-ui
                                      ◄── {profile: frame, source: ip:0}
        token username: oci/frame    ◄─ carried through the OCI middleware
```

The resolver chain lives entirely in the **metahub-admin-ui** inventory
service; metahub-api is a thin consumer. The inventory can grow (SQLite
store, edit UI, Netbox sync) without any consumer change.

## Resolution chain

`GET /api/v1/resolve?ip=<ip>` evaluates the sources in order, first match
wins:

| Order | Source | Mechanism | Configured via |
|---|---|---|---|
| 1 | **Runtime exact-IP** | ephemeral overlay entry (automation, e2e) | `POST /api/v1/entries` |
| 2 | **Static exact-IP** | operator statement, most specific | `inventory.entries` |
| 3 | **Hostname pattern** | DNS PTR of the client IP, case-insensitive regex, ordered | `inventory.hostname.rules` |
| 4 | **Learned** | remembered from the last explicit suffixed login from that IP (last-write-wins) | automatic — metahub-api reports explicit logins |
| 5 | **CIDR** | longest matching prefix (runtime overlay merged, runtime wins ties) | `inventory.entries` |

No match ⇒ `404 {}` — consumers fail open to `generic`. The resolve path
never answers `5xx`. PTR results (positive and negative) are cached for
`lookup_ttl`; transient DNS errors skip the hostname tier without caching.

An explicit suffixed login (`docker login -u oci/frame`) **skips resolution
entirely** — the operator always wins. It also *teaches*: metahub-api reports
the observation and the inventory remembers the ip→profile mapping as the
node's default (soft state, wiped when the inventory service restarts;
re-learning happens naturally at the next explicit login).

## Configure the inventory

Operator-managed sources live in the `inventory` config block (see the
example `misc/config/config.example.yaml` in metahub-admin-ui):

```yaml
inventory:
  entries:
    - ip: "192.168.5.115"          # exact-IP (optional display hostname)
      profile: "frame"
      hostname: "frame.hvk"
    - cidr: "192.168.5.0/24"       # subnet fallback
      profile: "generic"
  hostname:
    lookup_ttl: 60s                # PTR cache, incl. negative results
    rules:
      - pattern: '\.a100\.cluster\.example\.com$'
        profile: "gpu/a100"
```

Invalid sources (bad regex/CIDR/IP, empty profile) **fail startup naming the
offending entry**. Reload = restart (or SIGHUP) in v0.

## metahub-api consumer

metahub-api consumes the surface via an optional config block — **presence
of `url` enables resolution**; absent block ⇒ byte-identical legacy
behaviour:

```yaml
profile_resolution:
  inventory:
    url: "http://metahub-admin-ui.metahub-dev.svc.cluster.local"
    token_env: "INVENTORY_TOKEN"   # optional bearer token, never in YAML
    timeout: 2s
    cache_ttl: 60s                 # positive AND negative outcomes cached
```

Fail-open contract: inventory unreachable, timeout, `404`, malformed body ⇒
the profile stays `generic` and the login succeeds. The cache (positive and
negative, lazy expiry) keeps repeated auths from one node from hammering the
inventory; a successful explicit login clears that node's cached outcome so a
learned profile takes effect immediately.

## HTTP surface (v1, additive-only)

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/resolve?ip=<ip>` | the consumer surface: `200 {ip, profile, hostname?, source}` / `404 {}` |
| `GET /api/v1/inventory` | read-only snapshot (entries, hostname rules, effective TTL) |
| `GET /api/v1/health` | liveness for probes |
| `POST /api/v1/entries` | runtime entry (`{ip\|cidr, profile, hostname?}`) or learned entry (`{ip, profile, learned: true}`); 201 created / 200 updated / 409 duplicate |
| `DELETE /api/v1/entries?ip=\|cidr=` | remove a runtime/learned entry (static entries are not removable) |

When `INVENTORY_TOKEN` is set, all endpoints except `/health` require the
matching bearer token; unset ⇒ the service trusts the internal network.

The lookup UI (default page of the service) renders an IP lookup with the
winning source, and the inventory overview flags entries as **runtime**
(violet) or **learned** (indigo).

## Operations

- **Dev cluster**: the inventory runs at `adminui.dev.example.com`; sources
  are seeded via the `metahub-admin-ui-config` ConfigMap (flux).
- **E2E**: the `admin-ui-e2e_MR1_dev` GoCD pipeline proves the whole loop on
  every admin-ui/api deploy — the agent self-registers its own pod IP as a
  runtime entry, resolves it (`runtime-ip:` source), runs a suffix-less login
  and asserts the minted token carries the learned profile.
- **Cluster-node pulls**: docker pulls that originate **on a k8s node** are
  SNATed by the node's kube-proxy/flannel to the node's `flannel.1` address
  (`10.42.<podcidr>.0`) before they ever reach the gateway — seed cluster
  nodes by that address (see the dev ConfigMap for an example).
- **Trust caveat**: the client IP is the leftmost `X-Forwarded-For` entry —
  spoofable by external clients through the gateway. Acceptable today
  (profile choice, not authorization); a future `ClientTrafficPolicy` +
  `x-envoy-external-address` consumption can harden it.

## References

- Research note: `Metahub/docs/research/profile-resolution-from-network-identity`
  (WP #47) — the original resolver-chain vision.
- Session: `hostname-profile-resolution` — OpenSpec changes
  `add-admin-ui-inventory-service` (session), `add-inventory-service`,
  `add-runtime-entry-api`, `add-learned-entries` (metahub-admin-ui) and
  `hostname-profile-resolution` (metahub-api).
- DevDiary: `2026-09-16-1755` (skeleton + deployment), `2026-09-17-1000`
  (thin consumer), `2026-09-17-1230` (runtime API + e2e), `2026-09-18-0905`
  (node-originated SNAT gotcha).
