# MetaHub

MetaHub is a container image registry that takes the **context of a user**
into account to deliver the best-suited container image. It sits in front of an
OCI registry and computes profile-aware image indexes from a graph of
manifests, collections, rules and profiles.

This site is a guide to MetaHub's core capabilities, with concepts you can see
in the UI and try with standard OCI tooling.

<div class="grid cards" markdown>

-   :material-image-multiple: **[Small Images](small-images.md)**

    How layers compose into manifests, and how a single tag resolves across
    architectures.

-   :material-layers-edit: **[Manipulations](manipulations.md)**

    How MetaHub serves the best-suited image layers per profile — defaults
    and variants.

-   :material-package-variant-closed: **[ORAS Artefacts](oras-artefacts.md)**

    Pushing and discovering OCI artefacts (referrers) with `oras`.

-   :material-brain: **[Model Injection](models.md)**

    Delivering a large GGUF model composed into a runtime image, sized
    to the user's VRAM profile.

-   :material-cloud-download: **[Pull-Through Cache](pull-through-cache.md)**

    Mirroring and caching upstream images on demand, per profile.

</div>
