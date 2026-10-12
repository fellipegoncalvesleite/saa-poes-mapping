# Status of the paper package (2026-10-02, QC-1 revision)

## Computational and document status

- Manuscript (`main.typ` → `build/main.pdf`) and supplement (`supplement.typ` → `build/supplement.pdf`)
  are complete drafts built locally with Typst 0.15.0 (Python package).
- All numbers come from `generated/claims_register.json`; figures from `scripts/make_paper_figures.py`.
- A fresh reproduction from the hash-verified raw cache was run in a separate workspace; see the
  final verification report in `outputs/paper_finalization/20260929_phases4_6/VERIFICATION.md`; the
  QC-1 revision was reproduced again in a clean workspace on 2026-10-03
  (`outputs/paper_qc/20261002_noaa15_qc/final/VERIFICATION.md`, 39/39 steps, 300/300 files identical).

## Pending author actions (not done, not implied)

- **Author review** of the manuscript, the supplement and the critical-code walkthrough
  (`outputs/paper_finalization/20260929_phases4_6/CODE_WALKTHROUGH.md`). Nothing here states or
  implies that this review has happened.
- **Affiliation**: none is given in the manuscript. Add one only if the author has one to declare.
- **Funding statement**: omitted. No funding is known to this package.
- **Competing interests**: omitted. The author should state them (or "none") if a venue requires it.
- **Acknowledgements — PENDING AUTHOR/PERMISSION.** The manuscript carries a clearly marked draft
  sentence crediting François Ginisty for the flux × cell-area centroid weighting. Do not submit it until
  he has agreed to be named; he is not a coauthor. Xiaoheng Xu, whose preliminary assessment prompted the
  QC checks, is not named anywhere; ask him first if you want to thank him.
- **QC-1 decision**: the post-hoc exclusion of one NOAA-15 record is the author's decision to confirm
  (see `docs/qc_decision.md`). The paper reports the unfiltered result alongside.
- **Reader version**: a personal Portuguese reader (`paper/reader/build/`) uses the same claims
  register; it is not for publication.
- **Code/data availability**: the text says the final version is local and uncommitted, with no DOI.
  If the code is later pushed or archived, update section 6 with the actual commit and identifier.

## Out of scope by instruction

Venue choice, journal formatting, cover letters, publication fees and contacting cited authors.
