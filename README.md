# metahub-docs

MkDocs Material documentation site for MetaHub — the conference demo
walkthroughs (small images, layer manipulations, ORAS artefacts).

Served at **docs.metahub.hvk** (prod) and **docs.dev.example.com** (dev).

## Source layout

```
docs/                 Markdown pages (also consumed by qshuf for slides)
  index.md
  small-images.md
  manipulations.md
  oras-artefacts.md
  walkthrough.md
  assets/diagrams/    excalidraw exports (.svg) embedded in pages
mkdocs.yml            site config + nav (build runs --strict)
Dockerfile            2-stage: mkdocs build -> nginx serve
nginx.conf            static serving config
requirements.txt      mkdocs-material
```

## Local development

```bash
pip install -r requirements.txt
mkdocs serve            # live preview at http://127.0.0.1:8000
mkdocs build --strict   # what CI runs (fails on broken links/nav)
```

## Container

```bash
docker build -t metahub-docs .
docker run --rm -p 8080:80 metahub-docs   # http://localhost:8080
```

The CI **Test** stage builds the `build` target and runs
`mkdocs build --strict`; **Build** pushes the runtime image; **Deploy**
hot-patches the k8s deployment and syncs the new image into the flux repo.

## qshuf reuse

The `docs/*.md` files are plain Markdown with standard admonitions and fenced
code only — qshuf consumes the same source to build the slide deck. Keep
diagrams as standalone `.svg` under `docs/assets/diagrams/` so they embed in
both targets.
