# Agent Environment Composer

`outfitter` composes a versioned, reproducible agent harness — MCP servers,
skills, agents, commands, rules, and plugins — from pinned sources and renders it
into the target harness's native config, **vendored into your repo**. What the
agent runs is deterministic, offline-capable, and drift-checked in CI.

Think `go.mod`/`go.sum` for agent environments: a **manifest** declares intent
with loose refs; a **lockfile** pins exact versions and digests; a per-harness
**adapter** renders the vendored output. Resolution happens at **build time** —
nothing is fetched at agent startup.

<div class="grid cards" markdown>

-   :material-file-document: **Declarative manifest**

    One `agent.compose.yaml` describes your whole agent environment. Source
    of truth, reviewable in a PR.

-   :material-lock: **Lockfile**

    `agent.compose.lock` pins every component to an immutable digest —
    reproducible across machines and CI.

-   :material-file-cog: **Vendored output**

    `opencode.json` and `.opencode/` are committed to the repo. The agent
    starts instantly, no network required.

-   :material-shield-check: **Drift detection**

    `outfit verify` rebuilds from the lock and diffs against committed
    output. Run it in CI to block un-reviewed changes.

</div>

## Concepts

| File | Role | Editable by |
|---|---|---|
| `agent.compose.yaml` | manifest — declared intent with loose refs (image tags, version ranges) | human |
| `agent.compose.lock` | lockfile — exact pins (digest, version+integrity, capability snapshot) | `outfit lock` |
| `opencode.json` | rendered OpenCode config — the harness output | `outfit build` |
| `.opencode/*/` | vendored components (skills, prompts, agents) | `outfit build` |

## Quick start

### 1. Declare your environment

Create an `agent.compose.yaml` at the root of your project:

```yaml
version: 1
targets: ["opencode"]          # render to OpenCode

sources:
  metahub:                     # an OCI registry of agent components
    oci: "metahub.hvk/agent-components"

components:
  mcp:
    - name: sonarqube          # local, container-backed
      transport: { type: stdio }
      runner: { oci: "sonarsource/sonarqube-mcp", tag: "1.4" }
      env: { SONARQUBE_TOKEN: "{env:SONAR_TOKEN}" }

    - name: github             # remote HTTP endpoint
      transport: { type: http, url: "https://api.githubcopilot.com/mcp/" }
      headers: { Authorization: "Bearer {env:GITHUB_MCP_TOKEN}" }

  skills:
    - source: metahub          # vendored from the registry
      artifact: skills/go-review
      tag: v1.2
```

!!! tip "Secrets are references, never values"
    Use `{env:VAR}` to reference environment variables and `{file:./path}` for
    files. These pass through verbatim into the vendored config, so no secret is
    committed and rotating a token never causes drift.

### 2. Lock

Resolve every loose tag and version range to an immutable pin:

```bash
outfit lock
```

This produces `agent.compose.lock`:

```json
{
  "version": 1,
  "mcp": {
    "sonarqube": {
      "image": "sonarsource/sonarqube-mcp@sha256:abc123..."
    },
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "snapshot": { "tools": [...], "server_version": "1.2.3" }
    }
  },
  "components": {
    "skills/go-review": {
      "source": "metahub",
      "ref": "metahub.hvk/agent-components/skills/go-review@sha256:def456..."
    }
  }
}
```

=== "Local MCP servers"

    Tag is resolved to an **OCI digest**: `sonarqube-mcp:1.4` → `sonarqube-mcp@sha256:…`.
    The image is pulled by the container runtime — no tool installation needed.

=== "Remote MCP servers"

    Pins the URL **and captures a capability snapshot**: advertised tools,
    JSON schemas, and server version. `verify` can flag toolset drift even
    when the URL hasn't changed.

=== "Components (skills, rules, …)"

    Artifacts from an OCI registry are digest-pinned, then **unpacked into
    `.opencode/<key>/`** so the harness finds them without a network call.

### 3. Build

Render the vendored harness from the lock:

```bash
outfit build
```

This writes two kinds of output:

| Output | Content |
|---|---|
| `opencode.json` | MCP servers rendered as OpenCode entries (remote `url` or local `command` with pinned image) |
| `.opencode/skills/go-review/` | Skill files unpacked from the pinned OCI artefact |

The generated `opencode.json` for the example above:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "sonarqube": {
      "type": "local",
      "enabled": true,
      "command": [
        "docker", "run", "--rm", "-i",
        "-e", "SONARQUBE_TOKEN",
        "sonarsource/sonarqube-mcp@sha256:abc123..."
      ],
      "environment": {
        "SONARQUBE_TOKEN": "{env:SONAR_TOKEN}"
      }
    },
    "github": {
      "type": "remote",
      "enabled": true,
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer {env:GITHUB_MCP_TOKEN}"
      }
    }
  }
}
```

### 4. Verify (CI)

Rebuild and diff against the committed output:

```bash
outfit verify
```

If the lockfile and manifest produce output that doesn't match what's
committed, `verify` fails and tells you what drifted — block it in CI to
keep the repo and the agent in sync.

```yaml title="Example GitHub Actions step"
- name: Check agent drift
  run: outfit verify
```

## MCP server kinds

`outfitter` supports three classes of MCP server, each pinned differently:

| Transport | Runner | Resolution | Rendered as |
|---|---|---|---|
| `http` / `sse` | _none_ | URL + capability snapshot | `"type": "remote"` |
| `stdio` | `oci` — container image | digest (`@sha256:…`) | `"type": "local"` with `docker run` command |
| `stdio` | `npm` / `uvx` | version + integrity hash | `"type": "local"` with `npx` / `uvx` command |

!!! note "Container-based local servers"
    Local MCP servers with `runner.oci` are rendered as `docker run --rm -i`
    commands with environment variables injected. The `hosts` field in the
    runner maps hostnames to IPs and is rendered as `--add-host` flags — useful
    for reaching services on a known cluster IP without DNS.

### Remote MCP example

```yaml
components:
  mcp:
    - name: context7
      transport: { type: http, url: "https://mcp.context7.com/mcp" }
      headers: { CONTEXT7_API_KEY: "{env:CONTEXT7_API_KEY}" }
```

=== "Manifest (agent.compose.yaml)"

    ```yaml
    components:
      mcp:
        - name: context7
          transport:
            type: http
            url: "https://mcp.context7.com/mcp"
          headers:
            CONTEXT7_API_KEY: "{env:CONTEXT7_API_KEY}"
    ```

=== "Lock (agent.compose.lock)"

    ```json
    {
      "mcp": {
        "context7": {
          "url": "https://mcp.context7.com/mcp",
          "snapshot": {
            "tools": ["resolve-library-id", "query-docs"],
            "server_version": "1.0.0"
          }
        }
      }
    }
    ```

=== "Vendored (opencode.json)"

    ```json
    {
      "mcp": {
        "context7": {
          "type": "remote",
          "enabled": true,
          "url": "https://mcp.context7.com/mcp",
          "headers": {
            "CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}"
          }
        }
      }
    }
    ```

### OCI-backed MCP with host mapping

```yaml
components:
  mcp:
    - name: victoriatraces
      transport: { type: stdio }
      runner:
        oci: "ghcr.io/victoriametrics-community/mcp-victoriatraces"
        hosts: { "vt.example.com": "192.0.2.201" }
      env:
        VT_INSTANCE_ENTRYPOINT: "http://vt.example.com"
```

=== "Manifest"

    ```yaml
    components:
      mcp:
        - name: victoriatraces
          transport:
            type: stdio
          runner:
            oci: "ghcr.io/victoriametrics-community/mcp-victoriatraces"
            hosts:
              "vt.example.com": "192.0.2.201"
          env:
            VT_INSTANCE_ENTRYPOINT: "http://vt.example.com"
    ```

=== "Vendored"

    ```json
    {
      "mcp": {
        "victoriatraces": {
          "type": "local",
          "enabled": true,
          "command": [
            "docker", "run", "--rm", "-i",
            "--add-host", "vt.example.com:192.0.2.201",
            "-e", "VT_INSTANCE_ENTRYPOINT",
            "ghcr.io/victoriametrics-community/mcp-victoriatraces@sha256:…"
          ],
          "environment": {
            "VT_INSTANCE_ENTRYPOINT": "http://vt.example.com"
          }
        }
      }
    }
    ```

The `--add-host` flag is rendered per-entry from `runner.hosts`, so the
container can reach services by name without DNS.

## Components (skills, prompts, agents, rules)

Components are versioned artefacts stored in an OCI registry. Their lifecycle
mirrors MCP servers:

| Step | Command |
|---|---|
| Declare | Add to `components` in `agent.compose.yaml` with a source + tag |
| Lock | `outfit lock` resolves the tag to a digest |
| Build | `outfit build` pulls and unpacks the artefact into `.opencode/<key>/` |
| Verify | `outfit verify` re-pulls from the pinned digest and diffs the tree |

```yaml
sources:
  metahub:
    oci: "metahub.hvk/agent-components"

components:
  skills:
    - source: metahub
      artifact: skills/go-review       # stored as OCI/ORAS artefact
      tag: v1.2                        # loose version
```

After `outfit build`, `.opencode/skills/go-review/` contains the skill's
`SKILL.md`, scripts, and assets — ready for the harness to load at startup
with no network access.

## Resolve a reference

`outfit resolve` resolves a loose image ref to an immutable digest using the
caller's ambient registry login:

```bash
outfit resolve metahub.hvk/agent-components/skills/go-review:v1.2
# → metahub.hvk/agent-components/skills/go-review@sha256:abc123...
```

Already-pinned refs pass through unchanged:

```bash
outfit resolve registry.example.com/foo@sha256:abc123
# → registry.example.com/foo@sha256:abc123
```

## The three files in practice

Every change to the agent environment follows the same cycle:

```
agent.compose.yaml  ──outfit lock──▶  agent.compose.lock  ──outfit build──▶  opencode.json
                                                                           + .opencode/
                                            outfit verify ◀────────────────────┘
                                                  (CI drift gate)
```

1. **Edit** `agent.compose.yaml` — add an MCP server, bump a skill version, or
   wire a new component source.
2. **`outfit lock`** — resolve everything to digests. Commit the manifest and
   lockfile together.
3. **`outfit build`** — render the vendored harness. Commit the output.
4. **`outfit verify` runs in CI** — if it fails, a change slipped past
   `outfit lock` or someone edited the output by hand.

!!! info "The lockfile is what makes it reproducible"
    Even if a tag moves upstream (a new v1.2 push, a container retag), the
    lockfile pins the **exact digest** that was resolved.  Every `outfit build`
    from the same lock produces bit-identical output — across machines, CI
    runners, and time.

## Reference

```
outfit lock     resolve loose refs  → agent.compose.lock
outfit build    render vendored harness from lock
outfit verify   rebuild and diff against committed output (CI drift gate)
outfit resolve  resolve <image[:tag]> to image@sha256:…
```

| Flag | Applies to | Effect |
|---|---|---|
| `--strict-remote` | `lock` | Fail if a remote MCP capability snapshot cannot be taken (default: warn-only) |