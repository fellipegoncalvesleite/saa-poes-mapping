# Status of the paper package (2026-10-12, v1.0.0 release)

## Computational and document status

- Manuscript (`main.typ` → `build/main.pdf`) and supplement (`supplement.typ` → `build/supplement.pdf`)
  are complete drafts built locally with Typst 0.15.0 (Python package).
- All numbers come from `generated/claims_register.json`; figures from `scripts/make_paper_figures.py`.
- A fresh reproduction from the hash-verified raw cache was run in a separate workspace; see the
  final verification report in `outputs/paper_finalization/20260929_phases4_6/VERIFICATION.md`; the
  QC-1 revision was reproduced again in a clean workspace on 2026-10-03
  (`outputs/paper_qc/20261002_noaa15_qc/final/VERIFICATION.md`, 39/39 steps, 300/300 files identical).

## Resolved

- **Affiliation**: given in the manuscript and in `CITATION.cff`.
- **Code/data availability**: the code is in the public repository; Section 6 of the main text
  describes the package.
- **Acknowledgements**: final. Both people named have agreed to be named.
- **Review status**: the review-status notes have been removed from the manuscript and supplement.
- **QC-1 decision**: the post-hoc exclusion of one NOAA-15 record is adopted for the primary
  analysis (see `docs/qc_decision.md`); the paper reports the unfiltered result alongside.

## Open

- **Zenodo DOI**: once the v1.0.0 release is archived, replace the sentence in Section 6 that says
  the version will be released with an archival DOI with a citation of the archived release
  (version and DOI).

## Notes

- **Funding statement**: omitted. No funding is known to this package.
- **Competing interests**: omitted. State them (or "none") if a venue requires it.
- **Reader version**: a personal Portuguese reader (`paper/reader/build/`) uses the same claims
  register; it is not for publication.

## Out of scope by instruction

Venue choice, journal formatting, cover letters, publication fees and contacting cited authors.
