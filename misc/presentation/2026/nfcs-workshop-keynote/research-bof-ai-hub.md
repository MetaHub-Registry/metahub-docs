# Research — ISC 2026 BoF "Towards a federated European AI Hub"

> Source: `bof-ai-hub.pptx` (41 slides + notes).
> Parsed with **python-pptx 1.0.2** — faithful presentation order, tables, grouped shapes, and
> notes mapped to their own slide (an earlier regex pass mislabelled notes by one slide; corrected here).
> Event: **ISC 2026 · Birds of a Feather** — *Towards a federated European AI Hub — a technical angle*.
> Moderator: **Christian Kniep (QNIB Solutions)**. Contact: hpcw (at) qnib.org.
> This is our own material — reused freely into the NFCS Cambridge keynote (`keynote.md`).

## Why this matters for the NFCS keynote

The BoF and the NFCS keynote share the thesis (a registry now serves *anything*; on HPC that
couples to hardware; federation is a governance problem across actors). The BoF adds three
reusable assets the keynote lacked:

1. **An artefact taxonomy grouped by _behaviour → federation strategy_** (not file type). ← folded in.
2. **A "federate vs. reproduce" design principle** — the cut that shrinks the problem.
3. **A concrete prior-art landscape + a sharp "gap" statement**, and a **three-pillars** trade-off frame.

---

## 1. The artefact taxonomy — group by behaviour, not file type  (slide 6)

> *Grouped by how they behave — because that, not the file type, decides how you handle & federate them.*

| Behaviour | Artefacts | Federation strategy |
|---|---|---|
| **Heavy & static** | Container images (PyTorch, vLLM, TGI, CUDA/ROCm) · model weights & checkpoints (base, fine-tunes, LoRA, optimizer state) · datasets (training, fine-tuning, eval/benchmark) · compiled formats (GGUF, ONNX, TensorRT/ROCm engines) | **mirror / cache** |
| **Mutable state** | Embeddings & vector indices (continuously rebuilt) · RAG corpora (retrieval knowledge bases) · agent / session memory (stateful, per-run) | **sync** |
| **Lightweight & coupled** | Tokenizers & configs (must travel with the weights) · prompts (system, templates, few-shot) · skills & tools (MCP servers, function defs) · harness & pipelines (serving config, agent scaffolding) | **version-control** |
| **Metadata & trust** | Model cards & datasheets · lineage & provenance · signatures & attestations (cosign / sigstore) · SBOMs | **index & sign** |

This maps the keynote's "artifact zoo" onto an actionable handling model.

## 2. Design principle — federate vs. reproduce  (slide 31)

> *The cut that shrinks the problem: federate the canonical sources + the recipe; let each site rebuild the rest.*

- **Federate — canonical sources** (the truth a hub must hold & protect):
  - Model weights & checkpoints (base, fine-tunes, adapters)
  - Datasets & RAG source corpora (training, eval, the raw knowledge)
  - **Recipes** (training/build scripts, configs, env locks, seeds)
  - Metadata & trust (cards, lineage, signatures, SBOMs)
- **Reproduce locally — derived** (regenerable caches, not federation problems):
  - Compiled engines (TensorRT/ROCm, ONNX, GGUF — hardware-specific)
  - Embeddings & vector indices (rebuild from corpus + embed model)
  - Quantizations (GPTQ/AWQ — derivable from weights + recipe)
  - Agent / session memory (ephemeral, site-local)
- **The judgment call:** reproduce only works if the recipe is captured & deterministic — and
  federate anyway when *regeneration cost > transfer + storage cost* (e.g. a 70B quant, or an
  index over billions of docs).

## 3. Three pillars — and the floor they stand on  (slide 33)

- **Sovereignty & Governance** — data residency & jurisdiction · access control & licensing · who funds & operates it.
  *Trade-off: keep it in Europe vs. use the best/cheapest compute.*
- **Trust & Provenance** — signing & attestation · lineage & reproducibility · SBOM / supply-chain integrity.
  *Trade-off: verifiable & reproducible vs. velocity.*
- **Performance & Cost** — moving terabytes, caching, HPC I/O · storage replicated across N sites · egress fees & sustainability.
  *Trade-off: federate everywhere vs. what you can afford to move & store.* ("the part that actually kills federations")
- **Foundation — Interoperability & open standards.** Shared formats + a common metadata layer are the floor; without them none of the three pillars stand.
- 🗒 *Note: "How open is to open?"*

## 4. Framing — "federation" of what, exactly?  (slide 4)

Two different problems; the BoF is about the second, standing on the first:

- **Identity & resource access** (the plumbing): federated AuthN/AuthZ (MyAccessID, eduGAIN, EOSC),
  allocation & accounting, inter-site trust agreements. *Largely the EuroHPC Federation Platform's
  domain — heavyweight, organisational.*
- **Artifacts** (this BoF): distribute & discover models/data/embeddings/containers; provenance
  travels with the artifact; independent of where produced. *Depends on identity federation, but a
  separate, lighter, technical problem.*

> Notes (slide 4): EuroHPC-level federation is hard to join → national programmes go ahead with their
> own stacks → fragmentation becomes the default. **Artifact federation may be the lighter-weight,
> more joinable entry point — if we don't bolt it onto the heavyweight access layer.**

## 5. Prior art & the gap  (slide 7)

- **Model & artifact registries:** Hugging Face Hub · OCI + ORAS · KServe ModelCars · Ollama
- **HPC distribution fabric:** CVMFS (CERN) · Spack mirrors / build caches · Apptainer/Singularity · **EESSI**
- **Vendor ecosystems:** NVIDIA NGC / NIM · AMD Infinity Hub · CNCF OPEA
- **Federation & national efforts:** EuroHPC Federation Platform (CSC) · Genesis Mission (ORNL) · GAIA-X / AI-on-Demand
- **Supply-chain trust:** Sigstore / cosign · SLSA / in-toto · SBOM (SPDX, CycloneDX)
- **Solved analogues:** PyPI / conda mirrors · Linux distro mirror nets · CERN data federation

> **The gap:** *no sovereign, HPC-native, trust-aware fabric that federates models + data + provenance
> together — and nobody has solved the cost / egress problem at federation scale.*

## 6. Standards & panel questions  (slides 32, 34–38)

- **What standards to build on?** Open Knowledge Format · OCI, ORAS.
- **Optimize for what?** foundation-model fine-tuning · specialized model retraining · reproducible
  distillation · non-uniform quantization — *do we need to decide?*
- How to squeeze an AI Hub into EuroHPC (HPC infra + federated access)?
- How to stay open & inclusive without pushing our vision down? (🗒 slide 36: *CERN pushes their stack
  down to other centers and they don't like it — build something that scales down to the lowest level*.)
- How to fund it? carrots/sticks to onboard sites (🗒 slide 37: *a free helpdesk gets abused → need
  member buy-in, or a big funding carrot*; slide 38: *sites do want to get paid for collaboration*).
- How do the EU AI Act / Digital Markets Act affect federation?

---

## 7. Panelists & session structure

**Panel** (slide 2):

| Role | Person | Org | Angle |
|---|---|---|---|
| Moderator | Christian Kniep | QNIB Solutions | Containers in HPC · session host |
| EuroHPC | Henrik Nortamo | CSC | EuroHPC Federation Platform (technical lead) |
| Vendor | CJ Newburn | NVIDIA | Vendor ecosystem & artifact distribution |
| Vendor | Martin Hilgeman | AMD | Vendor ecosystem & ROCm |
| US perspective | Scott Atchley | ORNL | Genesis Mission |

**Four segments** (slide 3): (1) Building Blocks · (2) Current State & Challenges [US Genesis Mission +
EU EuroHPC] · (3) Vendor & Project Ecosystems [NVIDIA, AMD, +Intel/OPEA/HPE] · (4) The Future
(extended roundtable) — each = short lightning talk priming a roundtable, then open networking.

## 8. Notable positions

- **Henrik Nortamo / CSC — three challenges** (slide 13): **project model** (capabilities tied to a
  single fixed-duration project → data migration & access-control pain); **storage model** (compute is
  the only properly-tracked "currency"; storage is tacked on — large needs require a real process);
  **service delivery** ("same service, different address" · a central/common abstraction layer · "one"
  hub with proximity solved by caching/mirrors).
- **CJ Newburn / NVIDIA — "Model it vs. buffer it"** (slides 22–23; 🗒 slide 23; slides 40–41): biggest
  HPC-data challenge is capturing insight in a *shipped model* vs. sending raw data — filter at the
  instrument (GPUs), treat filtered unstructured data as a vector DB, index it, serve remote queries,
  ship the model (can be ~1e6× smaller) rather than the data. Converged storage; **GPUDirect
  RDMA / Storage**; move processing to data acquisition. Make AI a **first-class citizen in the data
  pipeline** (provenance, IP, federated learning, confidential computing, lifecycles, policies).
  Examples: Fast Radio Burst detection, real-time nanoimaging, climate-in-a-bottle, Vera Rubin Obs.
- **Scott Atchley / ORNL — Genesis Mission** (slides 9–11): US national effort connecting
  supercomputers, AI and quantum with scientific instruments; intelligence layer trained on National
  Lab datasets; five Lab-led teams under the American Science and Security Platform.

---

## Appendix — full slide-by-slide transcript

*(python-pptx, presentation order; speaker notes flagged 🗒 on the slide they belong to.)*

1. **Title** — ISC 2026 BoF · *Towards a federated European AI Hub — a technical angle.* "What the artefacts are, how we handle them, and how they could be federated?" Chips: Containers · Model weights · Datasets · Embeddings/RAG · Provenance & trust · Distribution.
2. **Overview & panel** — "A common hub for models, embeddings, vector DBs & RAG across EuroHPC. Non-commercial, community-driven — short lightning talks + moderated roundtables, live Q&A." (panel table in §7).
3. **Agenda** — four themed segments (Building Blocks · Current State & Challenges · Vendor & Project Ecosystems · The Future) + networking; "tentative — segments adapt to the room."
4. **Framing — "Federation" of what?** — identity/resource access vs. artifacts (§4). 🗒 fragmentation / joinable-entry-point (quoted in §4).
5. **Segment 1 divider** — Building Blocks.
6. **Building Blocks** — the behaviour→strategy taxonomy (§1).
7. **Current State & the gap** — prior-art landscape + gap statement (§5); tagline "US (Genesis Mission) + EuroHPC perspectives · EESSI".
8. **Segment 2 divider** — Current State & Challenges (US Genesis + EU EuroHPC).
9–11. **Scott Atchley / Genesis Mission (US)** — national AI+quantum+HPC discovery platform; integrates HPC, experimental facilities, data & production into one AI-driven discovery system; five Lab-led teams.
12–13. **Henrik Nortamo / EuroHPC (EU)** — "from clusters to a zoo of capabilities and services"; three challenges (project model, storage model, service delivery — §8).
14–19. **Segment 2 Q&A (public projects)** — US vs EU differences/commonalities/stakeholders; reach beyond initiating bodies (US DoE/labs, EU EuroHPC + national/industry/academia); fragmentation (AI Factories already publishing on Hugging Face); EU AI Act / DMA; identity federation as the MVP foundation & whether to broaden scope.
20. **Segment 3 divider** — Vendor & Project Ecosystems.
21. **Vendor & project landscape** — NVIDIA (NGC · NIM · CUDA containers · TensorRT) · AMD (ROCm · Infinity Hub · MI tuning) · Intel (oneAPI · OpenVINO · Gaudi · Tiber) · CNCF OPEA (composable GenAI/RAG blueprints) · HPE · other (model hubs, OCI registries, community tooling). 🗒 tension: vendor-optimized stacks vs. portable open formats — what to standardize?
22. **CJ Newburn / NVIDIA** — bio; "Model it vs. buffer it".
23. **CJ Newburn — ship model vs. raw data** — filter/real-time-adjust/inference-to-keep-interesting/train-on-interesting/index-search/queries/GPUDirect-transmit; examples (Fast Radio Burst, nanoimaging, climate-in-a-bottle, data-federation-mesh, The Weather Company, Vera Rubin Obs). 🗒 filter→vector-DB→index→remote-query→ship-model pipeline (~1e6× smaller); regenerate synthetic data at sites; real-time decisions.
24–26. **Martin Hilgeman / AMD** — bio; content placeholders.
27–29. **Segment 3 Q&A (vendors)** — where vendor stacks help vs. lock-in; what to standardize across vendors/projects (formats, metadata, trust; OPEA & community).
30. **Segment 4 divider** — Panel Discussion (design principles, federation models, sovereignty, governance, path forward).
31. **Design principle — federate vs. reproduce** (§2).
32. **Guiding questions** — optimize for what? (fine-tuning, retraining, reproducible distillation, non-uniform quantization; "do we need to decide?").
33. **Three pillars** — Sovereignty & Governance · Trust & Provenance · Performance & Cost · foundation Interoperability (§3). 🗒 "How open is to open?"
34–38. **Guiding questions (cont.)** — squeeze AI Hub into EuroHPC; standards (Open Knowledge Format, OCI/ORAS); open & inclusive without pushing vision down; funding/onboarding. 🗒 slide 36: CERN push-down anti-pattern / scale down to the lowest level. 🗒 slide 37: free-helpdesk-abuse vs. member buy-in / funding carrot. (slide 38: "sites want to get paid for collaboration".)
39. **Thank you** — segments recap; hpcw (at) qnib.org.
40. **Handling AI datasets** — make AI a first-class citizen in the data pipe: provenance (raw→model→synthesized), IP, federated learning, confidential computing, lifecycles, labeled-dataset orchestration, policies. 🗒 short/medium/long-term pressing issues for AI datasets (AI readiness & output).
41. **Novel technologies** — converged storage architectures; minimize storage SKUs across buffering/KV$/index-search; avoid buffer copies; GPUDirect RDMA & Storage; minimize data moved (process at acquisition, GPU-accelerated); send filtered/modeled data vs. raw; selective/indexed storage; model data; cold-storage archived discoveries. 🗒 rising storage-component cost (NVMe/disk/tape) & lead times.
