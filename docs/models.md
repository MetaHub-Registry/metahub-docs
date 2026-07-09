# Model Injection

MetaHub can deliver a large AI model — a multi-gigabyte GGUF file — as an image
**layer injected into a base image**, chosen by the user's **VRAM profile**. The
model is pushed **once** as an [ORAS artefact](oras-artefacts.md), repackaged
into an injectable model-layer image, and attached to a profile as a
[manipulation](manipulations.md). Pulling a base image under that profile then
overlays the model layer — the same base tag, but now carrying the model sized
for the host that asked for it.

This ties the two previous capabilities together: an **ORAS artefact** supplies
the payload, and a **manipulation** overlays it per profile — except the overlaid
layer is a model weighing tens of gigabytes rather than a small helper.

## The flow

| Step | Who | What |
|---|---|---|
| **1. Push** | model author | `oras push` the GGUF **and a per-profile config** (each blob tagged by media type) as one artefact |
| **2. Repackage** | operator | `metahub-admin repackage` splits the artefact by media type into a `models/<name>-layer` and a `models/<name>-config` image, attaching `model/<name>` (+ `config/<name>`) to a VRAM profile |
| **3. Pull** | user | `docker pull` a base image under the VRAM profile — the model **and its config** are injected |

## 1. Push the model as an artefact

The model arrives like any other ORAS artefact — no special upload path. Because
GGUF weights are large, MetaHub accepts the blob as a **chunked upload** and
streams it straight to object storage, so a 10–100 GB push never has to be
buffered in memory.

```bash
# Log in to the MetaHub registry
echo hub | oras login -u meta --password-stdin "{{ registry }}"

# Push the GGUF weights + a per-profile runtime config, each blob by media type
oras push "{{ registry }}/models/qwen3-8b:q8-kxl" \
  --artifact-type "application/vnd.qnib.model.artifact" \
  ./qwen3-8b-q8_k_xl.gguf \
  ./serve.json:application/vnd.qnib.model.config.v1+json
```

At this point MetaHub has registered an artefact — you can see it under **ORAS
Artefacts** — but nothing injects it yet. It is inert weights waiting to be
wired to a profile.

## 2. Repackage into an injectable model layer

`metahub-admin repackage` reads the stored artefact, rewraps its file(s) as an
**uncompressed-tar OCI layer**, and pushes a small model-layer image
(`models/<name>-layer:<quant-tag>`). It then creates a `model/<name>`
manipulation and links it to the target **VRAM profile**:

```bash
metahub-admin --config ./config.yaml repackage \
  --artifact-repo "models/qwen3-8b" \
  --artifact-type "application/vnd.qnib.model.artifact" \
  --name        "qwen3-8b" \
  --quant-tag   "q8-kxl" \
  --profile     "vram#12gb" \
  --registry-url "{{ registry }}" --registry-user "meta" \
  --registry-pass "hub"
```

The repackage streams the model a chunk at a time (constant memory, regardless of
model size), verifies the content digest end-to-end, and wires the resulting
model-layer image into the graph so a pull can resolve it without re-fetching the
original artefact.

!!! note
    `repackage` **attaches** the model to a profile — it does not rewrite the base
    image on disk. The base blobs stay shared; the model layer is overlaid per
    profile at pull time, exactly like a [manipulation](manipulations.md).

## 3. Pull under a VRAM profile

As with every other MetaHub feature, the profile comes from the login credential.
First, for reference, pull a base image with **no** model profile:

```{ .console .no-copy }
$ echo hub | docker login --password-stdin -u 'meta' {{ registry }}
Login Succeeded

$ docker pull --platform=linux/amd64 {{ registry }}/qnib/ftest:latest
$ docker inspect {{ registry }}/qnib/ftest:latest
```
```{ .json .no-copy }
"RootFS": {
    "Layers": [
        "sha256:8d78b2117a5b...",   // base layer
        "sha256:7b386a2af9d0..."    // base layer
    ]
}
```

**2 layers** — the plain base image. Now log in with the `vram#12gb` VRAM profile and
pull the same tag:

```{ .console .no-copy }
$ echo hub | docker login --password-stdin -u 'meta/vram#12gb' {{ registry }}
Login Succeeded

$ docker pull --platform=linux/amd64 {{ registry }}/qnib/ftest:latest
$ docker inspect {{ registry }}/qnib/ftest:latest
```
```{ .json .no-copy }
"RootFS": {
    "Layers": [
        "sha256:8d78b2117a5b...",   // base layer (shared)
        "sha256:7b386a2af9d0...",   // base layer (shared)
        "sha256:c0ffee00model...",  // model layer (qwen3-8b, q8-kxl)
        "sha256:c02f1900conf..."    // config layer (/model/qwen3-8b/config)
    ]
}
```

Same `:latest` tag, but the served image now carries **two extra layers** — the
model **and its config**, injected because the login asked for the `vram#12gb`
profile. The base blobs are untouched and shared; only the model and config layers
are new.

## Why the profile drives it

Sizing a model to the hardware is exactly the kind of user-context decision
MetaHub exists to make. A `model/<name>` manipulation can carry per-VRAM
**variants** the same way `glow-extended` carries per-architecture ones (see
[Manipulations → Defaults and variants](manipulations.md#defaults-and-variants)):

| Login selector | Model layer served | Fits |
|---|---|---|
| `meta/vram#12gb` | heavily quantized weights | a 12 GB consumer GPU |
| `meta/vram#128gb` | full-precision weights | a 128 GB data-center GPU |
| `meta` (no VRAM selector) | none — plain base image | any host |

One tag, one push of the weights, and each host pulls the largest model its VRAM
can hold — without the user choosing a quantization by hand.

## Serving config, per profile

Weights alone don't serve — the runtime needs a **config** (model path, context
size, how many layers to offload onto the GPU), and the right config differs per
VRAM tier. That's why the push in step 1 carries a **second blob** tagged with the
dedicated config media type `application/vnd.qnib.model.config.v1+json`.

`repackage` splits the artefact **by media type**: the GGUF becomes the model
layer, and the config blob becomes a **config layer** at `/model/<name>/config/`,
attached to the same VRAM profile as a sibling `config/<name>` manipulation. A
pull under the profile then injects **both** — the model *and* its config — and a
`QNIB_MODEL_CONFIG_DIR=/model/<name>/config` env var points a llama.cpp-style
entrypoint at it.

Push one config per profile (`vram#12gb`, `vram#128gb`) and each host gets the
config its GPU wants — the publisher writes the exact args; MetaHub only places
the bytes, never guessing them.

## What you see in the UI

| Concept | Where it shows up |
|---|---|
| The model | the **Models** tab — one card per model with its VRAM profiles and image variants (the `models/<name>-layer` / `-config` images are kept **out of Collections**) |
| The source artefact | **Artefacts**, as `models/<name>` — linked from the model card via its OCI subject reference |
| The injected layers | expand `qnib/ftest` under the VRAM profile — base layers + the model layer (and the config layer, when pushed) |
| The profile link | open the VRAM profile — its **Manipulations** section lists `model/<name>` (and `config/<name>`) |

!!! note
    The model layer is stored once and shared across every base image that
    injects it — pulling the model under two different base tags does not
    duplicate the weights in object storage.

## Diagram

![Model injection pipeline: an ORAS artefact carrying the GGUF model and a config blob is repackaged into model-layer and config-layer images attached to a VRAM profile; pulling qnib/ftest:latest injects nothing for meta, and a model layer plus a per-profile config layer for meta/vram#12gb and meta/vram#128gb](assets/diagrams/model-injection.png)

_Source: `docs/assets/diagrams/model-injection.excalidraw` (edit + re-render to update)._
