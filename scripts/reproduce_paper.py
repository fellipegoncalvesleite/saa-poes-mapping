"""Single entry point: regenerate every paper value, figure, table and document from raw inputs.

Run from repository root with the project environment active:

    python scripts/reproduce_paper.py --audit-baseline PATH/TO/baseline.tar.gz \
        --qc-evidence PATH/TO/poes_n15_20240119_raw.nc [--skip-site]

Steps (each logged to outputs/reproduction/logs/, summary in outputs/reproduction/summary.json):
 1. verify the 155 raw NOAA files against paper/inputs/raw_manifest_recorded.csv (SHA-256)
 2. execute notebooks 02–05c in dependency order (CP6 synthesis before and after 05c); QC-1 applies
 3. QC-1 ledger, population envelopes, perturbations and unfiltered sensitivity (outputs/qc_sensitivity);
    level-1a count-rate evidence for the excluded record (hash-checked evidence file); the NOAA-15
    exact-record omission replayed on unfiltered data (outputs/omission_sensitivity, provenance)
 4. replay the frozen Phase 3 protocol (outputs/channel_assurance); draws must hash-match the record
 5. temporal coverage vs conditional morphology (outputs/tables/cp4d_temporal_support*)
 6. replay the Phase 1 triage census with the preserved original extractor (outputs/audit_replay)
 7. export the site payload twice and require byte identity
 8. claims register, figures, supplementary tables, PDFs
 9. unit tests, artifact validators, and (unless --skip-site) site tests and build
Stops at the first failing step. Nothing is downloaded: missing raw files are an error.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "reproduction"
LOGS = OUT / "logs"
PY = sys.executable
FROZEN = json.loads((ROOT / "paper/inputs/frozen_hashes.json").read_text())
steps: list[dict] = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name: str, cmd: list[str], cwd: Path = ROOT, env: dict | None = None) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    e = {**os.environ, "PYTHONPATH": str(ROOT / "src"), **(env or {})}
    with (LOGS / f"{len(steps):02d}_{name}.log").open("w") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=cwd, env=e, stdout=log, stderr=subprocess.STDOUT)
    steps.append({"step": name, "command": " ".join(cmd), "exit": proc.returncode,
                  "seconds": round(time.time() - t0, 1)})
    print(f"[{'ok' if proc.returncode == 0 else 'FAIL'}] {name} ({steps[-1]['seconds']} s)", flush=True)
    if proc.returncode != 0:
        finish(failed=name)


def check(name: str, ok: bool, detail: str) -> None:
    steps.append({"step": name, "check": detail, "exit": 0 if ok else 1})
    print(f"[{'ok' if ok else 'FAIL'}] {name}: {detail}", flush=True)
    if not ok:
        finish(failed=name)


def finish(failed: str | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps({"failed_step": failed, "steps": steps}, indent=1) + "\n")
    sys.exit(1 if failed else 0)


NOTEBOOK_RUNNER = r'''
import sys, json, subprocess, nbformat
from pathlib import Path
from nbclient import NotebookClient
root, logs = Path(sys.argv[1]), Path(sys.argv[2])
kdir = logs / "kernel" / "kernels" / "repro"; kdir.mkdir(parents=True, exist_ok=True)
(kdir / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                                              "display_name": "repro", "language": "python"}))
import os; os.environ["JUPYTER_PATH"] = str(logs / "kernel")
for p in sorted((root / "notebooks").glob("*.ipynb")):
    if p.name.startswith("01_"):
        continue  # exploratory data-access test; not a scientific dependency
    if p.name.startswith("05c"):
        subprocess.run([sys.executable, "scripts/generate_cp6a_summary.py"], cwd=root, check=True)
    print("EXECUTE", p.name, flush=True)
    nb = nbformat.read(p, as_version=4)
    NotebookClient(nb, timeout=1800, kernel_name="repro", resources={"metadata": {"path": str(root)}}).execute()
    nbformat.write(nb, logs / ("executed_" + p.name))
    print("OK", p.name, flush=True)
subprocess.run([sys.executable, "scripts/generate_cp6a_summary.py"], cwd=root, check=True)
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-baseline", type=Path, required=True,
                    help="phase1/baseline.tar.gz (preserved original extractor and tables) for the census replay")
    ap.add_argument("--qc-evidence", type=Path, required=True,
                    help="poes_n15_20240119_raw.nc, the NCEI level-1a file read as QC-1 evidence (hash-checked)")
    ap.add_argument("--skip-site", action="store_true", help="skip npm test/build (e.g. without Node)")
    a = ap.parse_args()
    os.chdir(ROOT)

    # 1 inputs
    run("input_manifest", [PY, "scripts/write_input_manifest.py"])
    check("audit_baseline_hash", sha(a.audit_baseline) == FROZEN["phase1_baseline_archive_sha256"],
          "baseline archive matches recorded SHA-256")
    qc_hashes = json.loads((ROOT / "paper/inputs/qc_evidence_hashes.json").read_text())
    check("qc_evidence_hash", sha(a.qc_evidence) == qc_hashes.get(a.qc_evidence.name),
          "level-1a QC evidence file matches recorded SHA-256")
    check("protocol_hash", sha(ROOT / "paper/inputs/channel_assurance_protocol.json") == FROZEN["phase3_protocol_sha256"],
          "frozen Phase 3 protocol matches recorded SHA-256")

    # 2 dependency chain from raw files
    nb_logs = LOGS / "notebooks"
    nb_logs.mkdir(parents=True, exist_ok=True)
    runner = LOGS / "run_notebooks.py"
    runner.write_text(NOTEBOOK_RUNNER)
    run("notebooks_02_to_05c", [PY, str(runner), str(ROOT), str(nb_logs)])

    # 3–6 paper-specific evidence
    run("qc_sensitivity", [PY, "scripts/run_qc_sensitivity.py"])
    run("qc_raw_count_evidence", [PY, "scripts/qc_raw_count_evidence.py", "--l1a", str(a.qc_evidence.resolve())])
    run("omission_sensitivity", [PY, "scripts/run_omission_sensitivity.py"])
    run("channel_assurance_replay", [PY, "scripts/run_channel_assurance.py", "--output", "outputs/channel_assurance",
                                     "--protocol", "paper/inputs/channel_assurance_protocol.json"])
    check("frozen_draws", sha(ROOT / "outputs/channel_assurance/block_draws.json") == FROZEN["phase3_block_draws_sha256"],
          "replayed block draws are byte-identical to the frozen draws")
    run("temporal_support", [PY, "scripts/run_temporal_support.py"])
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(a.audit_baseline) as t:
            t.extractall(tmp, filter="data")
        run("audit_census_replay", [PY, "scripts/run_integrity_audit.py", "--source-root", f"{tmp}/src",
                                    "--tables", f"{tmp}/outputs/tables", "--processed", f"{tmp}/data/processed",
                                    "--output", "outputs/audit_replay"])
    for key, rel in (("phase1_census_sha256", "outputs/audit_replay/census.csv"),
                     ("phase1_candidates_sha256", "outputs/audit_replay/candidates.csv"),
                     ("phase2_omission_pairwise_sha256", "outputs/omission_sensitivity/pairwise.csv"),
                     ("phase2_omission_sensitivity_sha256", "outputs/omission_sensitivity/sensitivity.csv")):
        check(f"matches_{key}", sha(ROOT / rel) == FROZEN[key], f"{rel} equals recorded evidence")

    # 7 site payload, twice
    run("export_site_1", [PY, "scripts/export_site_data.py"])
    first = OUT / "viewer_data_first.json"
    shutil.copyfile(ROOT / "site/public/data/viewer_data.json", first)
    run("export_site_2", [PY, "scripts/export_site_data.py"])
    check("export_byte_identity", first.read_bytes() == (ROOT / "site/public/data/viewer_data.json").read_bytes(),
          "two exports from identical inputs are byte-identical")

    # 8 register, figures, documents
    run("claims_register", [PY, "scripts/build_claims_register.py"])
    run("figures_tables", [PY, "scripts/make_paper_figures.py"])
    run("documents", [PY, "paper/build.py"])

    # 9 verification
    run("unit_tests", [PY, "-m", "unittest", "discover", "-s", "tests", "-v"])
    for v in sorted((ROOT / "scripts").glob("validate_*.py")):
        run(v.stem, [PY, str(v.relative_to(ROOT))])
    if not a.skip_site:
        run("site_npm_ci", ["npm", "ci", "--no-audit", "--no-fund"], cwd=ROOT / "site")
        run("site_tests", ["npm", "test"], cwd=ROOT / "site")
        run("site_build", ["npm", "run", "build"], cwd=ROOT / "site")
    finish()


if __name__ == "__main__":
    main()
