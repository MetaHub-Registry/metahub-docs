## ADDED Requirements

### Requirement: Fast checks run on every contribution

`metahub-docs` SHALL run a fast check suite on every pull request and every push to
the default branch. The suite SHALL NOT require a container runtime, a database
or any project secret.

The suite SHALL include:

- `pip install -r requirements.txt`
- `misc/mkdocs-build.sh` (`mkdocs build --strict`)
- `pip-licenses` allowlist and generated `THIRD_PARTY_NOTICES.md`
- `gitleaks` with the committed `.gitleaks.toml`
- DCO trailer check
- outbound-host allowlist

#### Scenario: Pull request from a fork

- **WHEN** a pull request is opened from a fork
- **THEN** the fast suite runs with a read-only token
- **AND** every job completes without reading a secret
- **AND** the result is reported on the pull request

#### Scenario: Push to the default branch

- **WHEN** a commit lands on the default branch
- **THEN** the same fast suite runs and the `fast` aggregator reports it

### Requirement: A single aggregator check represents the fast lane

The repository SHALL expose an aggregator job named `fast` that depends on every
fast job and succeeds only if all of them succeed. Only this aggregator SHALL be
marked as a required status check at the visibility flip.

#### Scenario: One fast job fails

- **WHEN** any fast job fails or is cancelled
- **THEN** the `fast` aggregator fails

### Requirement: Public workflows are fork-safe by construction

Pull-request-triggered workflows SHALL NOT reference secrets, SHALL declare
`permissions` explicitly with `contents: read` at most, SHALL NOT use
`pull_request_target`, and SHALL pin every third-party action to a full commit
SHA.

#### Scenario: A check needs a private resource

- **WHEN** a fast check would need a project secret or special repository access
- **THEN** it is redesigned, moved to the integration lane, or dropped

### Requirement: Container-backed checks gate releases, not pull requests

Container-backed tests SHALL run in a separate integration workflow rather than
on the pull-request path. This repository currently has none, so the fast lane
is the complete suite and no integration workflow exists. A future
container-backed test SHALL get a separate release-time workflow rather than
being added to the fast lane.

#### Scenario: A container-backed test is added

- **WHEN** a test starts a container
- **THEN** it runs only in a separate integration workflow on release tags and
  on demand, never on a pull request

### Requirement: Secret scanning and DCO are enforced

Secret scanning SHALL use the committed `.gitleaks.toml`; an unreviewed finding
SHALL fail the job. Every commit in a pull request SHALL carry a
`Signed-off-by` trailer and the DCO job SHALL fail when one is missing.

#### Scenario: New secret in a change

- **WHEN** a change introduces a value that gitleaks reports and the path is not
  allowlisted
- **THEN** the secret-scanning job fails

#### Scenario: Commit without sign-off

- **WHEN** a pull request contains a commit without `Signed-off-by`
- **THEN** the DCO job fails and names the commit

### Requirement: Dependency licences and vulnerabilities are checked

The repository SHALL commit a licence allowlist and a generated
`THIRD_PARTY_NOTICES.md`. `pip-licenses` SHALL fail on a licence outside the
allowlist and on notices drift.

#### Scenario: Unlisted licence

- **WHEN** a dependency under a licence outside the allowlist is added
- **THEN** the licence job fails and names the dependency

### Requirement: Outbound hosts are allowlisted

Non-test source SHALL reference only hosts on `.github/outbound-allowlist.txt`.
A reference to any other host SHALL fail the job.

#### Scenario: Analytics endpoint added

- **WHEN** a change adds code that contacts a host not on the allowlist
- **THEN** the outbound-host job fails and names the host
