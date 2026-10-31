# DATA_SOURCES.md — Navitas-new Data Provenance

> `data/` is gitignored (see `.gitignore`). Raw files are not committed. This file records URL, license, local path, and what each dataset is used for. Report raw numbers, no rounding.

## 1. GECAD production-line scheduling + energy (core benchmark)

- **Record:** https://zenodo.org/record/4106746
- **DOI:** 10.5281/zenodo.4106746
- **Paper:** https://www.mdpi.com/1996-1073/14/2/462 (Mota et al., Energies 2021, 14, 462)
- **Files:** `Input_JSON_Schedule_Optimization.json`, `Output_JSON_Schedule_Optimization.json`
- **License:** not stated on the Zenodo record; cite, do not redistribute
- **Local:** `data/gecad/` (gitignored, keep only these two JSONs)
- **Used for:** Primary benchmark for `engine/` solver. `load.py` reads `Input_JSON_Schedule_Optimization.json` (3 machines, 275 task instances, 132 units, 6 days × 192 five-minute periods, T=1152). `engine.py` models the four constraints from the paper/case study: time leap (`DAY=192`), task order `Harden[1.5]` before `Harden[2]` (paired by count, per INPUT JSON direction), collision `Sublimation` vs `Harden[2]`, deadline (one request, period 960). Baseline and solver costs in `engine/RESULTS.md` are computed on this dataset only.

## 2. German industrial plant load profiles (peak / load-shape evidence)

- **Record:** https://zenodo.org/records/3899018
- **File:** `LoadProfile_20IPs_2016.csv` (semicolon-separated, header on row 2, some timestamps carry a trailing " b" at the October clock change)
- **License:** not stated on the record; cite
- **Local:** `data/german/` (gitignored)
- **Used for:** Peak and load-shape evidence only (e.g., peak-to-mean, diurnal shape). Not used for absolute kW scales in the solver. Referenced for comparison to justify solver's machine-capacity cap and tariff-peak assumptions.

## 3. Irish manufacturing facility, asset-level energy (idle + peak evidence)

- **DOI:** https://doi.org/10.5281/zenodo.19180972
- **Descriptor:** https://www.mdpi.com/2306-5729/11/5/101
- **License:** CC BY 4.0
- **Local:** `data/irish/` (about 1.2 GB unzipped: gitignored, keep summary CSVs only)
- **Used for:** Idle and peak evidence (asset-level 15-min aggregates, 43 assets, 172 asset-phase streams, 2025 observation). Used to inform idle/standby assumptions and peak-load validation, not for solver's absolute kW.

## 4. Solar Power Generation Data, India (real PV generation shape, 15-min)

- **Kaggle:** https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
- **File:** `Plant_1_Generation_Data.csv` (we use the shape only; unit scale unclear)
- **License:** not stated (Kaggle default terms apply; cite)
- **Local:** `data/solar_india/` (gitignored)
- **Used for:** Real PV generation shape (15-min) for solar-aware analysis. Only the normalized shape is used; absolute yield is ILLUSTRATIVE and configured per `engine/engine.py` (`pv_scale`). Not used for Pakistan absolute solar yield.

## 5. KIT industrial demand-side flexibility benchmark (optional, not yet downloaded)

- **Page:** https://publikationen.bibliothek.kit.edu/1000094324
- **DOI:** 10.35097/1172
- **License:** CC BY 4.0, about 97.8 MB
- **Local:** (not yet downloaded)
- **Used for:** Optional future benchmark for demand-side flexibility comparison. Not currently used in `engine/` solver or `RESULTS.md`. Listed for completeness.

---

## Examined and Rejected (mention in README, do not use)

- **Kaggle textile engineering production dataset:** https://www.kaggle.com/datasets/zara2099/textile-engineering-production-dataset
- **Reason:** synthetic generator fingerprints; energy uncorrelated with every input. Not used.

## Tariff Sources (cost-model inputs; keep as dated config, not constants)

- **NEPRA Feb 2026 rationalization (X-WAPDA DISCOs and KE):** https://nepra.org.pk/tariff/Tariff/Ex-WAPDA%20DISCOS/2026/TRF-100%20XWDISCOS%20AND%20KE%20RATIONALIZATION%20OF%20TARIFF%2011-02-2026%202935-57.pdf
- **FESCO FY2025-26 adjustment:** https://nepra.org.pk/tariff/Tariff/Ex-WAPDA%20DISCOS/2025/23-06-2025/TRF-605%20&%20TRF-606%20ADJUSTMENT-INDEXATATION%20FESCO%2023-06-2025%209297-9303.pdf
- **NEPRA tariff index page:** https://nepra.org.pk/tariff/Distribution%20XWDISCOs.php
- **News report used for B2 rates (Rs35.68 peak / Rs22.83 off-peak, Rs1,250/kW fixed):** https://www.dawn.com/news/1973828
- **Status:** B2 rates confirmed via news only. Peak window (18:30-22:30) and export price (Rs8.13) are **UNVERIFIED**. Mark them as assumptions in code (`engine/engine.py` → `pk_tariff()`) and `README.md`.

---

## Summary Table

| dataset | URL / DOI | license | local | used for |
|---------|-----------|---------|-------|----------|
| GECAD 4106746 | https://zenodo.org/record/4106746 DOI 10.5281/zenodo.4106746 | not stated | `data/gecad/` | core benchmark: `Input_JSON` → `engine/` solver, 0 violations checker |
| German 3899018 | https://zenodo.org/records/3899018 | not stated | `data/german/` | peak/load-shape evidence only |
| Irish 19180972 | https://doi.org/10.5281/zenodo.19180972 | CC BY 4.0 | `data/irish/` | idle + peak evidence |
| Kaggle India solar | https://www.kaggle.com/datasets/anikannal/solar-power-generation-data | not stated | `data/solar_india/` | PV shape only |
| KIT 1000094324 | https://publikationen.bibliothek.kit.edu/1000094324 DOI 10.35097/1172 | CC BY 4.0 | not yet downloaded | optional, not yet used |


