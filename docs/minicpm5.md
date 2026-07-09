# Showcase: serving MiniCPM5-1B

This walkthrough takes one real model — [`openbmb/MiniCPM5-1B`](https://huggingface.co/openbmb),
quantized to **Q8_0** — and serves it as a **running inference server on a GPU**
using nothing but a `docker login` selector and a `docker pull`.

This is **model-centric pull**: you pull a *model* (`models/qnib/minicpm5:q8-0`)
under a hardware profile, and MetaHub composes a ready-to-run image server-side —
the right runtime for your GPU, the model weights, and a per-profile serving
config, stacked into one image. The model **is** the image; there is no base
image to choose and nothing to assemble by hand.

The model here was served on a **Strix Halo** box (AMD Ryzen AI MAX+ 395 /
Radeon 8060S, `gfx1151`, 124 GB usable VRAM) via a ROCm `llama.cpp` runtime — but
nothing in the *user* flow is hardware-specific: the same `pull` + `run` composes
the model for whatever profile asked for it.

## What makes up the showcase

| Piece | Identity | Role |
|---|---|---|
| Model | `models/qnib/minicpm5:q8-0` | pulled directly; composed per requesting profile |
| Runtime | collection `qnib/llama-server` | resolves the vendor image (rocm / cuda / …) for the profile |
| Weights | `q8-0` GGUF | the model-layer image, stacked in as a layer |
| Config | `serve.json` | per-profile serving config (llama-server flags) |
| Profile | `frame` | the Strix Halo tier; selected at login as `meta/frame` |

## 1. How it was made available (operator)

A one-time setup wires the model into MetaHub. The GGUF is brought in as an ORAS
artefact, then `repackage` turns it into a model-layer image and wires it under
the `frame` profile, **bound to the `qnib/llama-server` runtime collection** (which
resolves the ROCm image for `frame`):

```bash
# 1. bring the GGUF into MetaHub as an ORAS artefact
oras cp harbor.example.com/library/models/minicpm5:q8-0 \
        "{{ registry }}/models/minicpm5:q8-0"

# 2. repackage it into a model-layer image + wire it under the `frame` profile,
#    bound to the qnib/llama-server runtime collection
metahub-admin --config ./config.yaml repackage \
  --artifact-repo models/minicpm5 \
  --artifact-type application/vnd.qnib.model.artifact \
  --name          qnib/minicpm5 \
  --quant-tag     q8-0 \
  --profile       frame \
  --runtime       qnib/llama-server
```

!!! note
    The runtime is a profile-resolved **collection** now (`collections/qnib/llama-server`),
    not a registered runtime — there is no `runtime register` step. The collection
    picks the vendor image (rocm for `frame`, cuda for an NVIDIA tier, …) at serve
    time. In the community edition the model and collection are declared as files
    (`models/qnib/minicpm5` + `collections/qnib/llama-server`) and seeded by `parse`.

## 2. Pull the model under your profile (user)

As with every MetaHub feature, the profile comes from the login credential —
`meta/frame` (password `hub`) selects the `frame` (Strix Halo) profile. Pulling
the model tag returns the image MetaHub composed for that profile:

```{ .console .no-copy }
$ docker login -u 'meta/frame' {{ registry }}
Password: hub
Login Succeeded

$ docker pull {{ registry }}/models/qnib/minicpm5:q8-0
$ docker inspect {{ registry }}/models/qnib/minicpm5:q8-0
```
```{ .json .no-copy }
"RootFS": {
    "Layers": [
        "sha256:1a2b3c...",   // runtime base (ROCm llama.cpp) — resolved from the qnib/llama-server collection for `frame`
        "sha256:c0ffee...",   // model layer  → /model/qnib/minicpm5/minicpm5-1b-Q8_0.gguf
        "sha256:c02f19..."    // config layer → /model/qnib/minicpm5/config/serve.json
    ]
}
```

MetaHub **composed** this image server-side for the `frame` profile: the ROCm
runtime **+** the `q8-0` weights **+** the per-profile config, stacked additively.
Pull under a plain `meta` login (no profile) and there is nothing runnable — the
model only resolves under a profile whose hardware can serve it.

## 3. Run it — the runtime serves the model on the GPU

The composed image's entrypoint discovers the GGUF under `/model/<org>/<name>/`,
reads the injected config dir (`$QNIB_MODEL_CONFIG_DIR`), and serves an
OpenAI-compatible API on port `8080`. The runtime is already baked into the image
MetaHub composed for your profile — ROCm for `frame`, CUDA for `bazzite` — so only
the GPU-passthrough flags differ per host:

=== "frame · AMD ROCm (Strix Halo)"

    Pulled under `meta/frame`; the AMD GPU is handed in with the KFD/DRI devices:

    ```{ .console .no-copy }
    $ docker run --rm -p 8080:8080 \
        --device /dev/kfd --device /dev/dri \
        {{ registry }}/models/qnib/minicpm5:q8-0
    >> MetaHub runtime: serving injected model /model/qnib/minicpm5/minicpm5-1b-Q8_0.gguf
    >> injected config dir: /model/qnib/minicpm5/config
    ggml_cuda_init: found 1 ROCm device: Radeon 8060S Graphics (gfx1151)
    llama_model_loader: loaded meta data ... general.name = MiniCPM5 1B
    main: server listening on http://0.0.0.0:8080
    ```

=== "bazzite · NVIDIA CUDA (RTX 3060)"

    The **same** `q8-0` tag, pulled under `meta/bazzite` — MetaHub composed the
    CUDA `llama.cpp` runtime (`sm_86`, 12 GiB tier) instead of ROCm. The NVIDIA GPU
    is handed in with `--gpus all`:

    ```{ .console .no-copy }
    $ docker run --rm -p 8080:8080 \
        --gpus all \
        {{ registry }}/models/qnib/minicpm5:q8-0
    >> MetaHub runtime: serving injected model /model/qnib/minicpm5/minicpm5-1b-Q8_0.gguf
    >> injected config dir: /model/qnib/minicpm5/config
    ggml_cuda_init: found 1 CUDA device: NVIDIA GeForce RTX 3060 (sm_86)
    llama_model_loader: loaded meta data ... general.name = MiniCPM5 1B
    main: server listening on http://0.0.0.0:8080
    ```

The model path, GPU offload (`-ngl 99`), host and port are all set by the
runtime's entrypoint — the user supplies none of them. The one model tag resolves
to a **different runtime image per profile**: each vendor image is pinned to its
profile in the `qnib/llama-server` collection, so `frame` gets the ROCm build and
`bazzite` gets the CUDA build — never the other way round.

## 4. Query the endpoint

Once healthy, hit the completion endpoint:

```{ .console .no-copy }
$ curl -s localhost:8080/health
{"status":"ok"}

$ curl -s localhost:8080/completion \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Q: What is the capital of France? A:","n_predict":24,"temperature":0.1}'
```
```{ .json .no-copy }
{
  "content": " Paris",
  "model": "/model/qnib/minicpm5/minicpm5-1b-Q8_0.gguf",
  "stop": true,
  "tokens_predicted": 18
}
```

The same server answers the OpenAI-style route too, so existing clients work
unchanged:

```bash
curl -s localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Name three primary colors."}]}'
```

## 5. Confirm it ran on the GPU

The server log names the backend it loaded — for the Strix Halo box, the ROCm
device and `gfx1151` architecture:

```{ .console .no-copy }
$ docker logs <container> | grep -iE 'gfx1151|ROCm|radeon'
ggml_cuda_init: found 1 ROCm device: Radeon 8060S Graphics (gfx1151)
```

With all layers offloaded (`-ngl 99`), MiniCPM5-1B-Q8_0 serves at interactive
speed — on the order of **~140 tokens/second** on the Radeon 8060S.

## What you see in the UI

| Concept | Where it shows up |
|---|---|
| The model | the **Models** tab — a `qnib/minicpm5` card with its `q8-0` variant and the `frame` profile |
| Its compositions | the card's **compositions** — the runnable `qnib/llama-server` + `q8-0` + config bundle, derived from the model's referrers |
| The source artefact | **Artefacts**, as `models/qnib/minicpm5`, linked from the card via its OCI subject reference |
| The composed layers | expand `models/qnib/minicpm5` under the `frame` profile — runtime base + the model layer + the config layer |

!!! note
    The GGUF is stored **once** and shared across every profile that composes it —
    serving MiniCPM5 for two different profiles does not duplicate the weights in
    object storage.

## Recap

```
# operator (once)
oras cp … models/minicpm5:q8-0
metahub-admin repackage --name qnib/minicpm5 --quant-tag q8-0 --profile frame --runtime qnib/llama-server
                                       ────────────────────
# user
docker login -u 'meta/frame'                        # select the profile
docker pull  …/models/qnib/minicpm5:q8-0            # composed for your profile
docker run --device /dev/kfd --device /dev/dri -p 8080:8080 …/models/qnib/minicpm5:q8-0
curl localhost:8080/completion …                    # served on the GPU
```

One pull under your profile, and the model lands — sized, composed, and served —
on whatever host asked for it.
