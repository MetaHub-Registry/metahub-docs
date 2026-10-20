# MetaHub profile extension — v1 (draft)

> **Status:** draft for the 1.0 release. This is a registry-side extension, not
> a change to the OCI Distribution Specification. Changes to v1 are additive;
> a breaking change ships as v2.

## 1. Scope

A standard OCI registry maps `repo:tag` to one manifest. MetaHub adds a second
input: the **profile** of the client. The pair `(repo, tag, profile)` selects a
manifest.

This document defines:

- how a profile is selected,
- how a profile is authored (profile, rule, collection, manipulation, model),
- the annotation convention used to match hardware,
- the conformance points an implementation must satisfy.

It does not define a new media type. The output is a normal OCI manifest or
index.

## 2. Profile selection

The registry resolves the profile at authentication time, in this order:

1. **Explicit** — the registry login username carries a suffix:
   `user/profile` (for example `alice/zen2`).
2. **Automatic** — when an inventory service is configured, the registry asks
   it which profile belongs to the client address.
3. **Fallback** — `generic`.

The resulting profile is carried in the registry token and applied to every
pull in that session. There is no per-request profile header in v1.

A client that switches profiles must re-authenticate; Docker and containerd
cache one credential per registry host.

## 3. Rule files

A rule is a named predicate over a manifest's platform or annotations.

```yaml
name: "cpu"
tag: "zen2"
type: "anno"
op: "eq"
key: "org.supercontainers.hardware.cpu.target.microarch"
value: "zen2"
```

| Field | Values |
|---|---|
| `name` / `tag` | identity of the rule; profiles refer to it as `name:tag` |
| `type` | `plat` (platform: `os`, `arch`, `variant`) or `anno` (OCI annotation) |
| `op` | `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `re` |
| `key` | platform field or annotation key |
| `value` | compared value; `re` uses a regular expression |

A rule with `type: anno` and a trailing wildcard key
(`org.supercontainers.hardware.cpu.*`) matches when any annotation under that
prefix exists.

## 4. Profile files

```yaml
rule: cpu:zen2=true && os:linux=true
manipulations:
  - label: "layer/glow#1.5.0"
hardware:
  gpu:
    vendor: nvidia
    model: "sm_90"
    vram_gb: 80
  system:
    ram_gb: 512
    cpu_cores: 64
```

| Field | Meaning |
|---|---|
| `rule` | boolean expression over rule labels; the profile matches when true |
| `manipulations` | ordered manipulations applied to matching manifests |
| `hardware` | optional physical target; required for model serving |

### Expression grammar (rule labels)

```text
expr    := term (("&&" | "||") term)*
term    := "!"? "(" expr ")" | label "=" "true"
label   := name ":" tag
```

- Equality uses a single `=` (not `==`).
- `&&`, `||`, `!`, and parentheses are supported.
- A term is true when the referenced rule matches the manifest.

### Hardware block

| Field | Meaning |
|---|---|
| `gpu.vendor` | `nvidia`, `amd`, …; selects the runtime variant |
| `gpu.model` | vendor model identifier |
| `gpu.product_name`, `gpu.gfx_family` | descriptive |
| `gpu.vram_gb` | VRAM capacity; used for quant fit |
| `gpu.cu_count`, `gpu.simd_count` | descriptive |
| `system.ram_gb`, `system.cpu_cores` | host capacity |

A profile with a GPU block and `vram_gb > 0` is model-serving capable.

## 5. Collection files

```yaml
name: qnib/llama-server
tag: latest
manifests:
  - image: registry.example.com/ai/llama-cpp:cuda13-2_sm86
    profile: bazzite
  - image: registry.example.com/ai/llama-cpp:rocm7.2.4_gfx1151
    profile: frame
```

| Field | Meaning |
|---|---|
| `name` / `tag` | the served reference |
| `manifests[].image` | upstream OCI reference |
| `manifests[].digest` | optional digest pin |
| `manifests[].platform` | optional platform override |
| `manifests[].profile` | authoritative profile binding for this manifest |
| `manifests[].annotations` | annotations attached at materialisation |

When `profile` is set, the manifest belongs to that profile regardless of its
image annotations. When absent, annotation and platform matching apply.

## 6. Manipulation files

```yaml
label: layer/glow#1.5.0
env:
  HPC3_HELP: /usr/share/hpc3/help.md
entrypoint:
  op: replace
  value: [/usr/bin/hpc3-help]
cmd:
  op: replace
  value: [/usr/bin/entry.sh]
variants:
  "arch:arm64=true":
    layers:
      - image: registry.example.com/layers/glow/base:arm64
  "arch:amd64=true":
    layers:
      - image: registry.example.com/layers/glow/base:amd64
    env:
      GLOW_SIMD: AMD64
```

| Field | Meaning |
|---|---|
| `label` | identity, referenced from a profile |
| `env`, `workdir`, `user`, `volumes` | default config changes |
| `entrypoint`, `cmd` | `replace`, `prepend`, or `append` operations |
| `layers` | layers appended to the source manifest |
| `variants` | expression → config block; the matching variant is merged over the defaults |

`layers[].select` accepts a Python-style slice (`[1:]`, `[0]`, `[-1]`) to pick
which layers from the source image are appended.

A manipulation produces a derived manifest with a new digest. The registry
records the source and the manipulation label; the served artefact does not
yet carry a portable provenance annotation (see the trust model).

## 7. Model files

```yaml
name: qnib/minicpm5
runtime: qnib/llama-server
quants:
  - { tag: q8-0, source: registry.example.com/models/minicpm5:q8-0 }
latest:
  default: best-fit
  overrides:
    - { rule: "hardware.gpu.vram_gb >= 100", quant: q8-0 }
config:
  default: { ctx_size: 32768, kv_cache_type: q8_0 }
  overrides:
    - { profile: frame, config: { ctx_size: 65536 } }
```

| Field | Meaning |
|---|---|
| `runtime` | collection providing the runtime image per profile |
| `quants[].tag` / `.source` | served quant tag and its OCI source |
| `latest.default` | default quant selection |
| `latest.overrides` | profile or hardware-rule → quant |
| `config.default` | default runtime configuration |
| `config.overrides` | profile or rule → configuration patch |

Override rules use **hardware fields**, not rule labels:

```text
hardware.gpu.vram_gb >= 100 && hardware.gpu.vendor = "amd"
```

`=`, `!=`, `>`, `>=`, `<`, `<=`, `&&`, `||`, and parentheses are supported.
String values are quoted; numbers are bare. A comparison against an absent
field is false. Exactly one of `profile` or `rule` is set per override; the
most specific matching rule wins.

## 8. Annotation convention (v1)

MetaHub reads the following annotation prefixes. They are not an OCI standard;
they are the project's convention, using the historical
`org.supercontainers` namespace.

| Prefix | Used for |
|---|---|
| `org.supercontainers.hardware.cpu.target` | `platform`, `microarch`, `generic` |
| `org.supercontainers.hardware.cpu.target.microarch` | `zen2`, `zen3`, `skylake`, … |
| `org.supercontainers.hardware.cpu.target.generic` | `x86_64_v3`, `x86_64_v4`, … |
| `org.supercontainers.hardware.cpu.arch` | CPU architecture family |
| `org.supercontainers.hardware.cpu.optimized.mode` / `.version` | optimisation metadata |
| `org.supercontainers.hardware.gpu.vendor` | `nvidia`, `amd` |
| `org.supercontainers.hardware.gpu.nvidia.model` | NVIDIA model identifier |
| `org.supercontainers.hardware.gpu.amd.model` | AMD model identifier |
| `org.supercontainers.mpi.implementation` | `mpich`, `openmpi`, … |
| `org.supercontainers.software.python.version.major` | Python major version |

Implementations SHOULD ignore unknown annotations and MUST treat a comparison
against a missing key as false.

## 9. Resolution algorithm

```text
profile = explicit-suffix or inventory(ip) or "generic"
manifest = lookup(repo, tag, profile)
if manifest is an index:
    manifest = select-platform(manifest, client platform)
for manipulation in profile.manipulations (in order):
    if expression(manipulation) matches:
        manifest = apply(manipulation, manifest)
return manifest
```

A pull by digest skips this algorithm entirely.

## 10. Conformance checklist

An implementation of this extension:

- [ ] accepts `user/profile` at the token endpoint and preserves the profile
      for the session;
- [ ] falls back to `generic` for anonymous or suffix-less pulls;
- [ ] can return different digests for the same `repo:tag` under different
      profiles;
- [ ] evaluates `plat` and `anno` rules with the operators in §3;
- [ ] supports `&&`, `||`, `!`, parentheses, and single `=` in rule
      expressions;
- [ ] treats a comparison against a missing annotation as false;
- [ ] applies manipulations in profile order and returns a normal OCI manifest
      or index;
- [ ] bypasses resolution for digest pulls;
- [ ] does not return a 5xx for an unresolvable profile (fall back or no-match);
- [ ] records the source manifest and manipulation label for derived manifests.

## 11. What this extension does not define

- A new media type or a new manifest field.
- A portable provenance annotation (roadmap).
- Registry-side signing (roadmap).
- A client-side profile header.
- A standardisation claim: this is a MetaHub extension, not an OCI standard.
