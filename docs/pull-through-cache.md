# Pull-Through Cache

MetaHub can act as a **caching pull-through mirror** in front of one or more
upstream registries. When a client pulls an image whose first path segment
matches a configured registry alias, MetaHub fetches it from upstream on
demand, applies the requesting profile's manipulations, and serves it — then
caches the base-layer bytes so later pulls are local.

## Configure an upstream registry

Pull-through is opt-in per registry via a `pull_through:` block. Registries
without it keep the existing behaviour, and only registries that also allow
anonymous pulls participate:

```yaml
registries:
  - name: registry.example.com      # the alias used in image paths
    url: registry.example.com       # the upstream endpoint
    tls: false
    allow_anon: true          # the upstream is pulled anonymously
    pull_through:
      enabled: true
      client_redirect: false  # false: proxy bytes; true: 307 the client upstream
      cache: async            # stream base layers into MetaHub in the background
      refresh_interval: 1h    # manifest TTL
      max_cache_bytes: 0      # 0 = unlimited
      workers: 4              # optional per-registry worker override
```

## Pull an upstream image

The image path is `<MetaHub>/<alias>/<upstream-repo>:<tag>`:

```{ .console .no-copy }
$ docker pull {{ registry }}/registry.example.com/library/alpine:3.24
```

On the first pull MetaHub discovers the upstream manifest, ingests it
(expanding a multi-arch index into its supported children), applies the
requesting profile's manipulations, and serves the **per-profile index**. The
same upstream tag therefore resolves to a MetaHub-computed index just like a
natively hosted image.

## Serve-stale manifests with async refresh

MetaHub stamps `last_refreshed` on the `(repo, tag)` when it ingests. On a
cached pull:

- **within `refresh_interval`** — served from the cache, with no upstream call;
- **past the interval** (or `refresh_interval: 0`) — served from the cache
  immediately, while an asynchronous upstream re-check runs in the background.
  If the upstream digest moved, subsequent pulls resolve to the new manifest. If
  upstream is unreachable, the stale manifest is served and a warning is logged.

Digest-addressed pulls bypass the TTL entirely (they are content-addressed).

## Blob delivery and caching

On a blob GET whose bytes are not present locally, MetaHub resolves the upstream
from the request repo prefix and:

- **`client_redirect: true`** — responds `307` to the upstream blob URL (the
  inbound `Authorization` header is stripped);
- **`client_redirect: false`** — proxies the upstream bytes to the client.

In both cases a **cache job** is enqueued. A bounded, in-process worker pool
streams the layer into MetaHub storage at constant memory. Jobs are
deduplicated per digest, skipped when the object is already stored, dropped when
the queue is full, and stop being enqueued once `max_cache_bytes` is reached.
Once the bytes are local, later pulls are served through the normal MetaHub
blob path (presigned redirect or stream).

## Observability

| Metric | Meaning |
|---|---|
| `metahub_pull_through_cache_jobs_total` | cache jobs by event (`enqueued`/`started`/`completed`/`failed`/`dropped`) and reason |
| `metahub_pull_through_cache_bytes_total` | bytes streamed into MetaHub storage |
| `metahub_pull_through_blob_total` | blob routing outcome (`hit`/`redirect`/`proxy`) |
| `metahub_pull_through_refresh_total` | manifest refresh outcome (`enqueued`/`ok`/`failed`) |
| `metahub_pull_through_cache_queue_depth` | pending cache jobs |

Logs carry a `pull_through` field, and the intercept, cache-job and refresh
paths emit OTLP spans.

## Scope

Upstreams must allow anonymous pulls — authenticated upstreams and cache
eviction are out of scope. Pull-through never bypasses MetaHub authentication:
the upstream fetch is the only anonymous leg. A repo that does not match an
enabled alias follows the existing MetaHub path unchanged.