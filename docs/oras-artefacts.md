# ORAS Artefacts

MetaHub speaks the OCI artefact + referrers API, so you can push arbitrary
artefacts with [`oras`](https://oras.land/) and discover them via the referrers
endpoint.

## Push an artefact

```bash
# Log in to the MetaHub registry
oras login -u "${OCI_USERNAME}" -p "${OCI_PASSWORD}" "${MH_HOST}"

# Create a tiny payload
echo "hello world" > artifact.txt

# Push it with a custom artifact type
oras push "${MH_HOST}/hello-artifact:v1" \
  --artifact-type "application/vnd.acme.rocket.config" \
  ./artifact.txt
```

Verify the stored `artifactType`:

```bash
oras manifest fetch "${MH_HOST}/hello-artifact:v1" --pretty \
  | jq -r .artifactType
# -> application/vnd.acme.rocket.config
```

## Referrers / discovery

Attach a referrer (e.g. a signature or SBOM) to an existing subject and then
discover it:

```bash
# Attach an artefact that references the subject
oras attach "${MH_HOST}/hello-artifact:v1" \
  --artifact-type "application/vnd.acme.sbom" \
  ./sbom.json

# Discover referrers of the subject
oras discover "${MH_HOST}/hello-artifact:v1" -o tree
```

## In the UI

The **ORAS Artefacts** view lists each artefact and, on a detail page, shows its
artifact type, layers, and referrers.

## Diagram

![ORAS referrers: SBOM and signature artefacts point at the hello-artifact:v1 subject; oras discover walks them back as a tree](assets/diagrams/oras-referrers.png)

_Source: `docs/assets/diagrams/oras-referrers.excalidraw` (edit + re-render to update)._
