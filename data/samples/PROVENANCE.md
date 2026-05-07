# Sample data provenance

Real files downloaded from the official **NOAA NCEI** POES/MetOp SEM‑2 archive during the
Checkpoint‑1 feasibility audit (**2026‑06‑07**). Public‑domain U.S. Government data, no
authentication. These are kept for offline notebook runs and are **git‑ignored by default**
(re‑downloadable from the URLs below).

## 1. `poes_n19_20240101_proc.nc`  — primary product (NetCDF‑4)
- **URL:** https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/noaa19/poes_n19_20240101_proc.nc
- **Satellite / date:** NOAA‑19 / 2024‑01‑01
- **Product:** L1b processed (calibrated flux + ephemeris + flags)
- **Size:** 5 800 360 bytes  ·  **Format:** NetCDF‑4 (HDF5; magic `\x89HDF\r\n\x1a\n`)  ·  `content-type: application/x-netcdf`
- **sha256:** `45b84acd431025ef0abb3c87a81735c9364f155e97fb3a264848dd9d85be8e3c`
- **Verification:** downloaded length == server `content-length`; key variables confirmed by
  scanning the file's HDF5 metadata (`lat, lon, alt, time, satID, mep_pro_tel0_flux_p1..p6,
  mep_pro_tel90_flux_p1..p6, mep_omni_flux_p1..p3, mep_ele_tel*_flux_e*, L_IGRF, MLT, mep_IFC_on`).
  Not opened with xarray in the audit environment (no netCDF library installed).

## 2. `poes_n19_20140102.txt`  — zero‑dependency fallback (ASCII)
- **URL:** https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l2/v01r00/txt/2014/noaa19/poes_n19_20140102.txt
- **Satellite / date:** NOAA‑19 / 2014‑01‑02
- **Product:** L2 legacy SWPC 16‑s‑averaged archive (count rates, uncorrected)
- **Size:** 2 246 816 bytes  ·  **Format:** ASCII, whitespace‑delimited, 1 header row + 5400 rows  ·  `content-type: text/plain`
- **sha256:** `e31a1b78560b16dc5eac9b2fceb64039713616d39c3c1565577c15c12278875d`
- **Verification:** read end‑to‑end with the Python standard library (no third‑party libs);
  41 columns incl. `sslat, sslon, folat, folon, lval, mlt, pas0, pas90, mep0p1..p6, mep90p1..p6,
  mepomp6..p9`.

### Verify locally
```bash
sha256sum poes_n19_20240101_proc.nc poes_n19_20140102.txt
```
