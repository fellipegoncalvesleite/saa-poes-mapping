"""Build the main paper and supplement PDFs with the Typst compiler (pip package `typst`).

Run from repository root: python paper/build.py
Requires paper/generated/values.typ (scripts/build_claims_register.py) and paper/figures
(scripts/make_paper_figures.py). Writes paper/build/{main,supplement}.pdf.
"""
from pathlib import Path
import sys

import typst

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "build"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name in ("main", "supplement"):
        src = ROOT / f"{name}.typ"
        if not src.exists():
            continue
        # Embedded fonts only and a fixed timestamp: output does not depend on host fonts or build time.
        pdf, warnings = typst.compile_with_warnings(str(src), root=str(ROOT), ignore_system_fonts=True,
                                                   timestamp=1790640000)  # 2026-09-29T00:00Z
        for w in warnings:
            print(f"[{name}] warning: {w}", file=sys.stderr)
        (OUT / f"{name}.pdf").write_bytes(pdf)
        print(f"built {OUT / (name + '.pdf')} ({len(pdf)} bytes)")


if __name__ == "__main__":
    main()
