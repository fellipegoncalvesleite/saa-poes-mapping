"""CP6A synthesis must not depend on CP5C, which is produced after it in a clean rebuild."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scripts.generate_cp6a_summary import build_summary  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
CP5C = "cp5c_multisatellite_magnetic_generality_summary.parquet"


@unittest.skipUnless((TABLES / CP5C).exists(), "canonical tables not generated")
class Cp6aDependencyOrderTests(unittest.TestCase):
    def test_summary_builds_without_cp5c_and_matches_full_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for p in TABLES.iterdir():
                if p.suffix in (".parquet", ".csv") and not p.name.startswith("cp5c_"):
                    shutil.copy2(p, Path(tmp) / p.name)
            without = build_summary(Path(tmp))
        pd.testing.assert_frame_equal(without, build_summary(TABLES))


if __name__ == "__main__":
    unittest.main()
