# CI sample gates

Issue #433 asks for one reviewable validation path that local runs, GitHub
Actions, and GitLab CI can share. The shared entry point is:

```bash
make ci
```

That target runs unit tests, the fast committed scheduler sample gate, and the
fortification checks. GitHub Actions and GitLab CI call the same target so the
meaning of a failure is the same on both platforms.

The GitHub Actions workflow pins third-party actions to full commit SHAs and
sets `permissions: contents: read`, because the jobs only need repository read
access plus artifact upload.

## Fast committed sample gate

The every-PR gate is:

```bash
make sample-gate SAMPLE_GATE_SCHEDULERS=pbs,sge,slurm SAMPLE_GATE_MAX_FAILURES=0
```

Sources:

- PBS: `qtop_py/contrib`
- SGE: `qtop_py/contrib`
- Slurm: every directory under `tests/plugins/slurm_samples`

Policy:

- `SAMPLE_GATE_MAX_FAILURES=0` is the default and means any failed scheduler
  case fails CI.
- Rendered qtop output, SVG terminal screenshots, stderr, command lines, and
  `summary.json` are written under `artifacts/sample-gate/`.
- Each qtop subprocess receives an isolated `HOME` under its artifact
  directory, so log creation does not depend on a writable runner home.
- CI uploads that artifact directory so reviewers can inspect the rendered
  output without rerunning locally.

## Python 3.6 / AlmaLinux 8 gate

Clusters still running RHEL8-family userspace need a dependency-light check.
The CI job uses an `almalinux:8` container and runs:

```bash
make compat-py36 PYTHON=python3
```

That target compiles `qtop_py` and `tools`, then runs the same fast sample gate
with artifacts under `artifacts/sample-gate-py36/`.

## Larger archived PBS sweep

The larger PBS corpus is intentionally not vendored in this repository. When
`fgeorgatos/qtop-test-repo` is available next to this checkout, run:

```bash
make test-pbs-samples \
  PBS_SAMPLES_DIR=../qtop-test-repo/qtop5/results \
  PBS_SAMPLE_LIMIT=10 \
  PBS_MAX_FAILURES=50 \
  PBS_SAMPLE_TIMEOUT=8
```

`PBS_SAMPLE_LIMIT` controls how many rendered `.ans` files are saved.
`PBS_MAX_FAILURES` enables a full-corpus scan and fails when the failed sample
count exceeds the configured budget. The command writes `manifest.json`,
`failures.json`, and `summary.json` under `PBS_OUTPUT_DIR`.

## Fortifications

`make fortifications` compares the current branch against
`FORTIFY_BASE_REF`, which defaults to `origin/develop`. It rejects:

- control, bidi, or non-ASCII characters added in the diff
- generated-looking or binary-looking changed paths
- any Python `eval()` call site in the source tree

The generated/binary path check is deliberately conservative because
`CONTRIBUTING.md` asks contributors not to store heavy artifacts in `qtop`.

## Independent structure reference

The same Makefile-as-contract shape is used by other open source projects that
need local, GitHub, and GitLab runs to converge on the same commands. One small
example is `mattermost/mattermost-mattermod`, which has a project `Makefile`
plus both `.github/workflows/ci.yml` and `.gitlab-ci.yml` wired around shared
project commands:

- https://github.com/mattermost/mattermost-mattermod/blob/master/Makefile
- https://github.com/mattermost/mattermost-mattermod/blob/master/.github/workflows/ci.yml
- https://github.com/mattermost/mattermost-mattermod/blob/master/.gitlab-ci.yml
