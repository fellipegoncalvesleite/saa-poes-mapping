# Source / claim ledger

Each cited source, what it was read for, where the support is, and how far it applies. Read 2026-09-29.
Metadata (authors, title, venue, volume, DOI) verified against Crossref/OpenAlex; NOAA documents read
in full text from the official PDFs (local copies and SHA-256 in the evidence directory
`outputs/paper_finalization/20260929_phases4_6/literature/`, not redistributed).

| Key | Read | Supports in this paper | Location | Applicability limits |
|---|---|---|---|---|
| green2013manual | full text | SEM-2 processing converts level-1B sensor data into level-2 physical-unit products and adds IGRF-derived field parameters; Table A-1 lists `mep_omni_flux_p1..p3` with minimum 0 | §1.1 p.7 (level-1B → level-2); IGRF handling p.12–14; Table A-1 begins p.15, OMNI rows p.17 | Table A-1 prints the OMNI unit as `#/cm2-s-str` without the per-energy factor; the file metadata and the ATBD definition (below) give per-MeV differential flux, which we adopt. Manual dates from 2013; it does not state which IGRF generation the 2024 files used. |
| machol2012atbd (QC-1, re-read 2026-10-02) | full text | §3.4 steps 3–6 p.19–20: the regular fit is skipped (simple fit used) when the summed raw count rate is < 25 s⁻¹, a derived non-overlapping count rate is negative, or the first-three-channel sum is < 1; also when \|γ\| > 8, the high-energy slope is positive, or the energy iteration does not converge; two-point fit needs C0, C1 > 0.01 and j(E0) > 2 j(E1); otherwise one-point fit with γ_default = −2.9 (from 2003 NOAA-15 two-point fits). §5.3 p.35: QA is flag-based; "single power law fits will be used frequently outside of SEP events". §5.4: bad inputs flagged −999 upstream | §3.4 p.19–20; §5.3–5.4 p.35 | No automatic criterion for single-record departures; the event's count-rate pattern is matched to these steps by inference ("consistent with"), not from software output. Garbled multi-column text on p.19 was read with care; the 25 s⁻¹ threshold is the documented step-3 value. |
| machol2012atbd | full text | OMNI fluxes are power-law fits (piecewise, in energy) to count rates from four overlapping omni channels (16–35, 35–250, 70–250, 140–250 MeV); outputs are differential fluxes at 25, 50, 100 MeV in ions/(cm² s sr MeV); fit flag −1 = no fit, 0/1/2 = fit types | §3.1 p.10; §3.3 p.14; Table 4 p.24–25; Table 5 p.25 | Defines the fitted estimand and flag semantics; it does not declare fit 1 invalid and does not describe `mep_IFC_on = −1`. Software version per file not given. |
| ncei_sem2 | file metadata | Archive path l1b/v01r00; file `processing_level` = "Level 2, calibrated fluxes"; title warns of known contamination problems; per-variable units `#/cm2-s-str-MeV` | NetCDF global/variable attributes (event dossier) | The directory name is not the product level. |
| lin2019crosscal (QC-1, re-read 2026-10-02) | full text §2.2 | "The scattered points and the points with constant fluxes … are clearly erroneous"; removed "by manual processing" from every 2-month segment of each POES/MetOp satellite; erroneous data attributed generally to contamination, saturation, background noise and invalid measurement (citing Bourdarie et al. 2008) | §2.2, p.6910–6911 | Precedent that erroneous isolated OMNI points occur and are removed in published work; their removal is manual and not an automatic threshold, so it does not supply QC-1's parameters. |
| lin2019crosscal | full text (abstract, §1–2 skimmed, key points) | POES/MetOp proton omni data show calibration inconsistencies; cross-calibration by pairwise polynomial fits of **>16 MeV integral** fluxes, 1978–2014, referenced to NOAA-15 | Abstract; Key Points, p.6906 | Different quantity (integral >16 MeV, older 8-s product), period and processing. Its coefficients are **not** applied here; cited as the reason absolute intensities are not compared. |
| xu2025storm | abstract | Multi-satellite NOAA/MetOp ≥35/≥70/≥140 MeV proton maps of the SAA with a 3-day running average versus ~1-month averaging; ~20% SAA flux decline in May 2024 storm | Abstract | Integral channels, multi-satellite pooling, storm period; cited as context on averaging-window choice, not as validation of our windows. |
| qin2014solarcycle | abstract | NOAA-15 proton data 1999–2009 used to study long-term SAA variation (peak flux, area, location) with Gaussian fits | Abstract | Long-term, different fitting; context only. |
| furst2009rxte | abstract | Particle-background (RXTE) measurements of SAA strength/location; westward drift ~0.3°/yr | Abstract | Different instrument/altitude; context for SAA location as an estimated, method-dependent quantity. |
| schaefer2016saa | abstract | Particle-noise-based SAA model at fixed altitude/local time; centroid drift estimates | Abstract | Different instrument; context only. |
| kunsch1989block | abstract | Block resampling for stationary dependent observations | Abstract | Stationarity assumptions not established for 31 days; cited to describe the method family, not to claim calibrated inference. |
| synowiecki2007mbb | abstract | Sufficient conditions for moving-block bootstrap consistency under periodic/almost-periodic nonstationarity (mean-type parameters) | Abstract | Conditions not verified for our nonlinear footprint statistic. |
| harris2020numpy, hunter2007matplotlib | metadata | Software used | — | — |
| naturalearth | repository metadata in `site/public/data/geography.json` | Coastlines in maps | — | Display only. |

Not cited (could not be read in this session, or not needed): Evans & Greer (2000) SEM-2 instrument
memorandum (cited inside the NOAA manual; not read here); Casadio & Arino (2011) and Heirtzler (2002)
(abstracts not retrievable; omitted rather than cited from memory).

QC evidence file (not a literature source): NOAA/NCEI level-1a `poes_n15_20240119_raw.nc` (SHA-256 in
`paper/inputs/qc_evidence_hashes.json`), variables `mep_omni_cps_p6..p9`, `mep_pro_tel{0,90}_cps_p1..p6`,
`mep_ele_tel{0,90}_cps_e1..e3`, `mep_omni_biase_V`; record times identical to the processed file. NCEI's
POES known-issues page (now redirecting to https://www.ncei.noaa.gov/products/poes-space-environment-monitor)
notes that P8 and P9 share a telemetry word and are read out alternately, which explains the alternating
−1 values in those channels. No NOAA statement about this specific record was found.
