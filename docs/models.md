# Model Injection

MetaHub can deliver a large AI model — a multi-gigabyte GGUF file — as an image
**layer composed into a runtime image**, chosen by the user's **VRAM profile**.
The model is pushed **once** as an [ORAS artefact](oras-artefacts.md), repackaged
into an injectable model-layer image, and attached to a profile as a
[manipulation](manipulations.md), **bound to a runtime collection**. Pulling the
**model** (`models/<name>:<quant>`) under that profile then composes the runtime
base + model weights + serving config into one image — sized and wired for the
host that asked for it.

This is a **model-centric pull**: the model *is* the image. A plain base image
pulled under the same profile is served **un-injected** — see
[Collections are never model-injected](#collections-are-never-model-injected).

This ties the previous capabilities together: an **ORAS artefact** supplies the
payload, and a **manipulation** overlays it per profile — except the overlaid
layer is a model weighing tens of gigabytes rather than a small helper.

## The flow

| Step | Who | What |
|---|---|---|
| **1. Push** | model author | `oras push` the GGUF **and a per-profile config** (each blob tagged by media type) as one artefact |
| **2. Repackage** | operator | `metahub-admin repackage` splits the artefact by media type into a `models/<name>-layer` and a `models/<name>-config` image, attaching `model/<name>` (+ `config/<name>`) to a VRAM profile, **bound to a runtime collection via `--runtime`** |
| **3. Pull** | user | `docker pull models/<name>:<quant>` under the VRAM profile — the runtime, model **and its config** are composed |

## 1. Push the model as an artefact

The model arrives like any other ORAS artefact — no special upload path. Because
GGUF weights are large, MetaHub accepts the blob as a **chunked upload** and
streams it straight to object storage, so a 10–100 GB push never has to be
buffered in memory. Uploads are **content-addressed**: if a blob whose digest is
already in object storage is pushed again — a repeat push, or a re-seed — MetaHub
skips the upload, so identical weights are never sent or stored twice.

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
manipulation and links it to the target **VRAM profile**, **bound to a runtime
collection** (so a model pull knows which base image to compose onto):

```bash
metahub-admin --config ./config.yaml repackage \
  --artifact-repo "models/qwen3-8b" \
  --artifact-type "application/vnd.qnib.model.artifact" \
  --name        "qwen3-8b" \
  --quant-tag   "q8-kxl" \
  --profile     "vram#12gb" \
  --runtime     "qnib/llama-server" \
  --registry-url "{{ registry }}" --registry-user "meta" \
  --registry-pass "hub"
```

The repackage streams the model a chunk at a time (constant memory, regardless of
model size), verifies the content digest end-to-end, and wires the resulting
model-layer image into the graph so a pull can resolve it without re-fetching the
original artefact.

!!! note
    `repackage` **attaches** the model to a profile — it does not rewrite the
    runtime image on disk. The runtime blobs stay shared; the model layer is
    overlaid per profile at pull time, exactly like a
    [manipulation](manipulations.md). The `--runtime` flag records which
    collection the model composes onto — without it the model has no composition
    and a model-centric pull cannot resolve.

## 3. Pull the model under a VRAM profile

As with every other MetaHub feature, the profile comes from the login credential.
First, for reference, pull the model with **no** model profile — the runtime
collection resolves, but no model is composed:

```{ .console .no-copy }
$ echo hub | docker login --password-stdin -u 'meta' {{ registry }}
Login Succeeded

$ docker pull --platform=linux/amd64 {{ registry }}/models/qwen3-8b:q8-kxl
$ docker inspect {{ registry }}/models/qwen3-8b:q8-kxl
```
```{ .json .no-copy }
"RootFS": {
    "Layers": [
        "sha256:8d78b2117a5b...",   // runtime base layer (resolved from the collection)
        "sha256:7b386a2af9d0..."    // runtime base layer
    ]
}
```

**2 layers** — the runtime image alone. Now log in with the `vram#12gb` VRAM
profile and pull the **same model tag**:

```{ .console .no-copy }
$ echo hub | docker login --password-stdin -u 'meta/vram#12gb' {{ registry }}
Login Succeeded

$ docker pull --platform=linux/amd64 {{ registry }}/models/qwen3-8b:q8-kxl
$ docker inspect {{ registry }}/models/qwen3-8b:q8-kxl
```
```{ .json .no-copy }
"RootFS": {
    "Layers": [
        "sha256:8d78b2117a5b...",   // runtime base layer (shared)
        "sha256:7b386a2af9d0...",   // runtime base layer (shared)
        "sha256:c0ffee00model...",  // model layer (qwen3-8b, q8-kxl)
        "sha256:c02f1900conf..."    // config layer (/model/qwen3-8b/config)
    ]
}
```

Same `models/qwen3-8b:q8-kxl` tag, but the served image now carries **two extra
layers** — the model **and its config** — composed because the login asked for the
`vram#12gb` profile. The runtime base blobs are untouched and shared; only the
model and config layers are new.

## Collections are never model-injected

A model serving manipulation only applies to **model-centric pulls**
(`models/<name>:<quant>`). Pulling a plain **collection** image — the runtime, or
any other base image — under the same VRAM profile serves that image **as-is**:
the model is not injected.

```{ .console .no-copy }
$ echo hub | docker login --password-stdin -u 'meta/vram#12gb' {{ registry }}

# A collection pull under the model profile is served un-injected:
$ docker pull --platform=linux/amd64 {{ registry }}/qnib/llama-server:latest
$ docker inspect {{ registry }}/qnib/llama-server:latest
```
```{ .json .no-copy }
"RootFS": {
    "Layers": [
        "sha256:8d78b2117a5b...",   // runtime base layer
        "sha256:7b386a2af9d0..."    // runtime base layer
    ]
}
```

No model, no config — just the collection image. This keeps the two concepts
clean: a **collection** is an opinionated, profile-filtered image index (no model
injection); a **model** is a runtime image with the model and its config composed
as extra layers. Non-model manipulations (see [Manipulations](manipulations.md))
still apply to collection pulls — only the model-serving stack is gated to
model-centric pulls.

## Why the profile drives it

Sizing a model to the hardware is exactly the kind of user-context decision
MetaHub exists to make. A `model/<name>` manipulation can carry per-VRAM
**variants** the same way `glow-extended` carries per-architecture ones (see
[Manipulations → Defaults and variants](manipulations.md#defaults-and-variants)):

| Login selector | Model layer served | Fits |
|---|---|---|
| `meta/vram#12gb` | heavily quantized weights | a 12 GB consumer GPU |
| `meta/vram#128gb` | full-precision weights | a 128 GB data-center GPU |
| `meta` (no VRAM selector) | none — runtime image alone | any host |

One model tag, one push of the weights, and each host pulls the largest model its
VRAM can hold — without the user choosing a quantization by hand.

## Serving config, per profile

Weights alone don't serve — the runtime needs a **config** (model path, context
size, how many layers to offload onto the GPU), and the right config differs per
VRAM tier. That's why the push in step 1 carries a **second blob** tagged with the
dedicated config media type `application/vnd.qnib.model.config.v1+json`.

`repackage` splits the artefact **by media type**: the GGUF becomes the model
layer, and the config blob becomes a **config layer** at `/model/<name>/config/`,
attached to the same VRAM profile as a sibling `config/<name>` manipulation. A
model pull under the profile then injects **both** — the model *and* its config —
and a `QNIB_MODEL_CONFIG_DIR=/model/<name>/config` env var points a
llama.cpp-style entrypoint at it.

Push one config per profile (`vram#12gb`, `vram#128gb`) and each host gets the
config its GPU wants — the publisher writes the exact args; MetaHub only places
the bytes, never guessing them.

## What you see in the UI

| Concept | Where it shows up |
|---|---|
| The model | the **Models** tab — one card per model with its VRAM profiles and image variants (the `models/<name>-layer` / `-config` images are kept **out of Collections**) |
| The source artefact | **Artefacts**, as `models/<name>` — linked from the model card via its OCI subject reference |
| The composed layers | expand `models/<name>` under the VRAM profile — runtime base + the model layer (and the config layer, when pushed) |
| The profile link | open the VRAM profile — its **Manipulations** section lists `model/<name>` (and `config/<name>`) |

!!! note
    The model layer is stored once and shared across every base image that
    composes it — serving the model for two different profiles does not duplicate
    the weights in object storage.

## Diagram

![Model injection pipeline: an ORAS artefact carrying the GGUF model and a config blob is repackaged into model-layer and config-layer images attached to a VRAM profile; pulling models/qwen3-8b:q8-kxl composes the runtime base alone for meta, and the model layer plus a per-profile config layer for meta/vram#12gb and meta/vram#128gb](assets/diagrams/model-injection.png)

_Source: `docs/assets/diagrams/model-injection.excalidraw` (edit + re-render to update)._
