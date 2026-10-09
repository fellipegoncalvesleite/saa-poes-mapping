"""Content-addressed snapshot of the current working tree's sources (tracked + relevant untracked).

Run from repository root: python scripts/snapshot_sources.py OUTDIR
Writes OUTDIR/source_snapshot.tar.gz and OUTDIR/SOURCE_MANIFEST.json (HEAD, tracked-diff SHA-256,
per-file SHA-256). Generated outputs, raw data, caches, evidence trees and the site payload are
excluded so that a reproduction must rebuild them.
"""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import tarfile

EXCLUDE_PREFIXES = ("outputs/", "work/", "data/raw/", "data/processed/", "paper/build/", "paper/generated/",
                    "paper/figures/", "paper/tables/", "paper/reader/build/", "site/node_modules/", "site/dist/", ".venv/")
EXCLUDE_FILES = {"site/public/data/viewer_data.json"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main() -> None:
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    files = set(git("ls-files").splitlines()) | set(git("ls-files", "--others", "--exclude-standard").splitlines())
    keep = sorted(f for f in files if Path(f).is_file()
                  and (not f.startswith(EXCLUDE_PREFIXES) or f in ("data/processed/PROVENANCE.md", "data/samples/PROVENANCE.md"))
                  and f not in EXCLUDE_FILES and not f.endswith(".DS_Store")
                  and not str(Path(f).resolve()).startswith(str(out)))
    manifest = {"head": git("rev-parse", "HEAD").strip(), "branch": git("branch", "--show-current").strip(),
                "tracked_diff_sha256": hashlib.sha256(git("diff", "--binary").encode()).hexdigest(),
                "files": {}}
    with tarfile.open(out / "source_snapshot.tar.gz", "w:gz") as tar:
        for f in keep:
            data = Path(f).read_bytes()
            manifest["files"][f] = hashlib.sha256(data).hexdigest()
            info = tarfile.TarInfo(f)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    manifest["file_count"] = len(keep)
    manifest["content_sha256"] = hashlib.sha256(json.dumps(manifest["files"], sort_keys=True).encode()).hexdigest()
    (out / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(keep)} files; content {manifest['content_sha256'][:16]}; head {manifest['head'][:12]}")


if __name__ == "__main__":
    main()
