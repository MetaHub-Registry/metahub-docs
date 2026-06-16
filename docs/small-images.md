# Small Images

The demo uses a deliberately small, reproducible image set so the audience can
follow every layer. Two families are seeded:

- **Glow layers** — tiny single-purpose layers used to show layer composition.
- **Multi-arch alpine** — a small base used to demonstrate index aggregation
  (`amd64` + `arm64` under one tag).

## Seeding the set

The images are seeded idempotently from the compose Taskfile:

```bash
# Bring the stack up
task compose:up

# Seed the demo images + graph (glow layers, multi-arch alpine)
task compose:seed:glow
task compose:multi-alpine
```

After seeding, the graph computes the manifests and manifest lists:

```bash
task compose:seed:graph
```

## What you see

| Concept | Where it shows up |
|---|---|
| Individual layers | `/collections` in the UI, expand a manifest row |
| Manifest (single arch) | manifest detail, with config + layers inline |
| Manifest list (multi-arch) | one tag resolving to `amd64` / `arm64` |
| Content size | shown per manifest (the real blob size) |

!!! tip "Keep it minimal for a live audience"
    Seed only the glow set and one multi-arch base. Larger sets make the graph
    harder to read on a projector.

## Diagram

![Image / layer model: layers compose per-arch manifests that converge into one multi-arch manifest list](assets/diagrams/image-layer-model.png)

_Source: `docs/assets/diagrams/image-layer-model.excalidraw` (edit + re-render to update)._
