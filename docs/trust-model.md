# Trust model

MetaHub deliberately changes what `repo:tag` means: the tag resolves against a
**profile**, so the same tag can return different, valid content for different
clients. That is the feature. It is also the property most likely to be
misread, so this page states exactly what is and is not guaranteed.

## The short version

- A tag is **not** immutable across profiles. The digest depends on the
  profile used to resolve it.
- **Pull by digest** for strict, profile-independent content.
- The registry **records** manipulation derivations internally (source
  manifest + manipulation label). The served OCI artefact does **not** yet
  carry a portable provenance annotation.
- Registry-side signing of derived artefacts is **not** part of 1.0.
- Integrity is anchored at the registry boundary (TLS + authentication) and by
  digest pinning. It is not anchored in a signature on the transformed
  artefact.

## What a pull returns

1. The client authenticates at `/auth`. The username may carry a profile
   suffix (`alice/zen2`).
2. Without a suffix, metahub-api may ask the optional inventory service which
   profile belongs to the client IP.
3. Without either, the profile is `generic`.
4. The pair `(repo, tag)` plus the profile selects a **slot**. The slot's
   manifest — possibly a manipulated variant — is returned.

Different profiles can therefore produce different manifests, different layer
sets, and different digests for the same `repo:tag`.

## Digest pinning is the strict mode

A pull by digest (`docker pull registry/repo@sha256:…`) bypasses profile
resolution and returns exactly that manifest. Use it when you need:

- reproducible deployments,
- content that is identical across machines,
- a reference that a signature can describe unambiguously.

```bash
docker pull registry.example.com/library/app@sha256:…
```

Pinning is also the right answer for CI: resolve once under a known profile,
record the digest, and deploy the digest.

## Manipulations and what is recorded

A manipulation derives a new manifest from a source manifest. The registry
keeps the derivation:

- the manipulated manifest's label is `<source-label>#<manipulation>`;
- the graph links the derived manifest to its source (`MANIPULATED_FROM`);
- the derived manifest has its own digest, config, and layers.

This is auditable **through the registry**. It is not yet a portable
annotation on the artefact: a client that receives the manifest cannot read
the source digest and manipulation set from standard OCI metadata. Adding that
annotation is on the [roadmap](https://github.com/MetaHub-Registry/metahub-api/blob/main/ROADMAP.md)
as a "Next" item.

## Signing

Not provided in 1.0.

- A publisher signature over the **original** digest does not describe the
  transformed output.
- MetaHub does not sign derived artefacts in 1.0.
- A design for registry-side signing (cosign or a signed resolution index) is
  a roadmap item. Until then, do not present a MetaHub pull as a verified,
  signed artefact.

## What is not protected

- **A compromised registry** can serve different content. TLS and
  authentication protect the channel and the caller, not the operator's
  integrity.
- **Profile spoofing.** The login suffix is client-controlled. The inventory
  tier trusts the client address (including forwarded headers, when enabled);
  a client that can choose its apparent address can choose its profile.
- **Client-side tag caching.** Docker and containerd cache credentials per
  registry host. Switching profiles requires logging out and back in; a cached
  tag may keep serving the previous profile's content until refreshed.

## Practical guidance

| Need | Do this |
|---|---|
| Reproducible deployment | Pin the digest |
| Verify what you received | Compare the digest, not the tag |
| Different hardware on the same tag | Select a profile explicitly (login suffix) or run the inventory service |
| Strict supply chain | Pin digests, restrict push access, and treat the registry as a trusted component |
| Audit a manipulation | Inspect the derived manifest's label and source link in the registry |

## Summary

MetaHub moves part of the resolution decision from the client to the registry.
That is a deliberate trade: less per-node configuration, in exchange for a
registry that must be trusted and clients that must pin digests when they need
immutability. The documentation will not describe a tag as immutable across
profiles, and it will not describe an unsigned transformation as verified.
