#!/usr/bin/env python3
"""Run qtop against archived PBS samples and save rendered output.

Usage:
    python tools/validate_pbs_samples.py /path/to/qtop-test-repo/qtop5/results --limit 100 --output /tmp/qtop-pbs-rendered
    python tools/validate_pbs_samples.py /path/to/qtop-test-repo/qtop5/results --limit 10 --max-failures 50 --output /tmp/qtop-pbs-rendered
"""

import argparse
import json
import os
import subprocess
from pathlib import Path


GOLDEN_PBS_SAMPLES = (
    "gef_yBVifVBTyE44AKnehzSrvA",
    "gef_y2pQK8d9fstnQElgx8wuCw",
    "gef_xwILYNMpoabX4PDGYXIZAA",
    "gef_wd3MkxlAScZhd6-vEQakrg",
    "gef_kbgwjKhQ6rWy2ZFn_JkHgA",
    "gef_chUMytd1bwcB5Cbc59FHRA",
    "gef_i2OQxcmsYH3GAQnonKVqoA",
    "gef_nYSEKsd7-JpjqvOfI8UyNg",
    "gef_Ab0XLTIet2_e9SoSN-TV1g",
    "gef_BiUgx8_5M6to8nP2BPBcfg",
)


def _tail(text, lines=5):
    return text.splitlines()[-lines:]


def render_sample(sample_dir, output_dir, timeout, save_output):
    qtop_home = output_dir / ".home" / sample_dir.name
    qtop_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(qtop_home)
    try:
        proc = subprocess.run(
            ["./qtop", "-b", "pbs", "-s", str(sample_dir), "-c", "ON"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return None, {
            "sample": sample_dir.name,
            "status": "timeout",
            "timeout": timeout,
            "stdout_tail": _tail(exc.stdout or ""),
            "stderr_tail": _tail(exc.stderr or ""),
        }

    if proc.returncode != 0 or not proc.stdout.strip():
        return None, {
            "sample": sample_dir.name,
            "status": "failed",
            "returncode": proc.returncode,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
        }

    entry = {
        "sample": sample_dir.name,
        "stderr_tail": _tail(proc.stderr),
    }

    if save_output:
        output_file = output_dir / ("%s.ans" % sample_dir.name)
        output_file.write_text(proc.stdout)
        entry["output"] = output_file.name

    return entry, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("samples_dir", type=Path)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("/tmp/qtop-pbs-rendered"))
    parser.add_argument("--timeout", type=int, default=8, help="Per-sample timeout in seconds")
    parser.add_argument("--max-failures", type=int, default=None, help="Scan the full corpus and fail if more samples fail than this budget")
    parser.add_argument(
        "--skip-golden-samples",
        action="store_true",
        help="Do not force the curated 10-sample golden set into the rendered output.",
    )
    args = parser.parse_args()

    sample_dirs = sorted(path for path in args.samples_dir.iterdir() if path.is_dir())
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    failures = []
    seen = set()
    scanned = 0
    passed = 0

    if not args.skip_golden_samples:
        for sample in GOLDEN_PBS_SAMPLES[: args.limit]:
            sample_dir = args.samples_dir / sample
            if not sample_dir.is_dir():
                raise FileNotFoundError(f"golden PBS sample not found: {sample_dir}")
            scanned += 1
            entry, failure = render_sample(sample_dir, args.output, args.timeout, len(manifest) < args.limit)
            if failure is not None:
                failures.append(failure)
                if args.max_failures is None:
                    raise RuntimeError(f"golden PBS sample failed to render: {sample_dir}")
                seen.add(sample_dir.name)
                continue
            entry["golden"] = True
            manifest.append(entry)
            passed += 1
            seen.add(sample_dir.name)

    for sample_dir in sample_dirs:
        if args.max_failures is None and len(manifest) >= args.limit:
            break
        if sample_dir.name in seen:
            continue
        scanned += 1
        entry, failure = render_sample(sample_dir, args.output, args.timeout, len(manifest) < args.limit)
        if failure is not None:
            failures.append(failure)
            continue
        passed += 1
        manifest.append(entry)

    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (args.output / "failures.json").write_text(json.dumps(failures, indent=2))
    summary = {
        "rendered": len(manifest),
        "passed": passed,
        "failed": len(failures),
        "scanned": scanned,
        "limit": args.limit,
        "max_failures": args.max_failures,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        "rendered=%s passed=%s failed=%s scanned=%s output=%s"
        % (summary["rendered"], summary["passed"], summary["failed"], summary["scanned"], args.output)
    )
    if args.max_failures is not None:
        return 0 if len(failures) <= args.max_failures else 1
    return 0 if len(manifest) >= args.limit else 1


if __name__ == "__main__":
    raise SystemExit(main())
