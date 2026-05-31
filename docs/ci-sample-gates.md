# CI sample gates

Issue #433 asks for one reviewable validation path that local runs, GitHub
Actions, and GitLab CI can share. The shared entry point is:

```bash
make ci
```

That target runs unit tests, the fast committed scheduler sample gate, and the
fortification checks. GitHub Actions and GitLab CI call the same target so the
meaning of a failure is the same on both platforms.

Provider-specific aliases such as `make github-ci`, `make gitlab-ci`,
`make github-build`, and `make gitlab-build` deliberately resolve back to the
same Makefile targets. The YAML files stay thin and provider-facing while the
actual validation contract remains local and reviewable.

The GitHub Actions workflows pin third-party actions to full commit SHAs and
set `permissions: contents: read`, because the jobs only need repository read
access plus artifact upload.

Python packages installed by CI, including transitive helper packages, are
pinned in `requirements-ci.txt`; both GitHub Actions and GitLab CI install from
that same file before calling the Makefile targets. `make build` uses
`python -m build --no-isolation` so the build backend also comes from those
pinned CI requirements instead of being resolved dynamically during the build.

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
  `summary.json` are written under `artifacts/sample-gate/`, including for
  non-zero and timeout failures.
- Each qtop subprocess receives an isolated `HOME` under its artifact
  directory, so log creation does not depend on a writable runner home.
- CI uploads that artifact directory so reviewers can inspect the rendered
  output without rerunning locally.
- `qtop_py/contrib/func_tests.sh` delegates to this same sample gate, so the
  historical manual wrapper exercises the current CI path instead of carrying a
  separate drift-prone shell implementation.

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

## Coverage roadmap

The Makefile exposes:

```bash
make coverage
```

That target runs `coverage.py` through the same `PYTHON` override used by the
other targets. To enable coverage in CI without changing the abstraction,
install `requirements-ci.txt` and insert `make coverage` in the modern Python
job after `make ci`, then publish `coverage xml` or terminal summary artifacts
from the workflow. The AlmaLinux 8 / Python 3.6 lane should stay
dependency-light and continue to run `make compat-py36`.

## Develop / CONTRIBUTING.md alignment

Rechecked on 2026-05-31 against `origin/develop` and the current
`CONTRIBUTING.md`: the PR targets `develop`, keeps generated screenshots and
logs as CI artifacts rather than repository files, uses DCO signed commits, and
documents the AI-assisted validation surface in the pull request body.

## Independent structure reference

The same Makefile-as-contract shape is used by other open source projects that
need local, GitHub, and GitLab runs to converge on the same commands. One small
example is `mattermost/mattermost-mattermod`, which has a project `Makefile`
plus both `.github/workflows/ci.yml` and `.gitlab-ci.yml` wired around shared
project commands:

- https://github.com/mattermost/mattermost-mattermod/blob/master/Makefile
- https://github.com/mattermost/mattermost-mattermod/blob/master/.github/workflows/ci.yml
- https://github.com/mattermost/mattermost-mattermod/blob/master/.gitlab-ci.yml
