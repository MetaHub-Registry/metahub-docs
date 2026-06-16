# Manipulations

A **manipulation** rewrites an image's layers before it is served, based on the
resolved **profile**. This is how MetaHub turns one stored image into the
best-suited variant for a given user context.

Manipulation definitions live in the community-edition repo under
`manipulations/` (e.g. `manipulations/layer/`), and are parsed into the graph by
`metahub-admin`:

```bash
metahub-admin --config "${CONFIG}" parse manipulations ./community-edition/manipulations
```

## Defaults and variants

A manipulation has a **default** form and zero or more **variants**. The
profile selects which variant applies; if none match, the default is used.

| Form | When it applies |
|---|---|
| `default` | No matching variant for the resolved profile |
| `variant` | A profile attribute matches the variant's selector |

In the UI, open a profile at `/profiles/:label` — the **Manipulations** section
lists the default plus any variants (the `ManipulationCard` component).

## What you see in the demo

1. Pull a tag **without** a profile → the default layers.
2. Pull the same tag **with** a profile context → the manipulated layers.
3. Inspect both manifests side by side in `/collections`.

!!! note
    Manipulations are computed into the graph at parse time, then applied at
    resolution time. The stored blob set is shared; only the manifest the
    client receives differs per profile.

## Diagram

![Manipulation pipeline: the resolved profile selects a variant or falls back to the default, producing a per-profile served manifest](assets/diagrams/manipulation-pipeline.png)

_Source: `docs/assets/diagrams/manipulation-pipeline.excalidraw` (edit + re-render to update)._
