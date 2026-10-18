# 03: Datasets

Four data sources. All live in the parent `URECA_Code/` folder and are **not** committed
here (size, and third-party licensing).

---

## 1. TIGER datasets (primary)

`tiger-main/tiger_full/data-processed/`, bzip2-compressed pandas frames. Use
`DECOMPRESSION.py` in that folder, or `pd.read_pickle(..., compression='bz2')`.

| File | Contents |
|---|---|
| `off-target.bz2` | **primary dataset**: HEK293T survival screen |
| `off-target-nt.bz2` | non-targeting controls for the above |
| `hap-titration.bz2` | HAP1 titration validation screen |
| `hap-titration-nt.bz2` | non-targeting controls for the above |
| `flow-cytometry.bz2` | Wessels/Méndez-Mancilla 2020 flow-cytometry screen |
| `data_preview_10rows.csv` | **start here**: plain-text 10-row sample of the schema |

### Schema

From `data_preview_10rows.csv`:

- **Identity:** `gene`, `guide_id` (e.g. `crRNA0349:349-371`), `guide_type`
- **Activity (the label):** `lfc_r1`, `lfc_r2`, `lfc_r3`, log-fold change per replicate.
  Work averaged these into `mean_lfc`. **More negative = more active** (an active guide
  kills the cell, so its barcode depletes).
- **Sequence:** `guide_seq` (23 nt spacer), `target_seq`, `5p_context`, `3p_context`
- **Location features:** `loc_utr_5p`, `loc_cds`, `loc_utr_3p`, `log_gene_len`,
  `junction_dist_5p`, `junction_dist_3p`
- **Structural/thermodynamic features:** `direct_repeat`, `g_quad`, `mfe`,
  `hybrid_mfe_1_23`, `hybrid_mfe_15_9`, `hybrid_mfe_3_12`, `log_unpaired`,
  `log_unpaired_11/19/25`, `guide_fold`, `target_fold`

The `hybrid_mfe_*` and `log_unpaired*` columns are the **baselines that outperformed every
structural oracle** (see `04_results.md`). They were already in the dataset, no extra
computation needed.

`guide_type` values: **`PM`** = perfect match, **`SM`** = single mismatch (titration
series, e.g. `..._SM_P1-A:G` = position 1, A→G). Filter to `PM` unless you specifically
want mismatch tolerance.

`COLUMN_EXPLANATIONS.md` in `tiger-main/tiger_full/` documents the *prediction output*
multi-index (`context`, `features`, `filter-method`, `loss`, `model` = `Tiger2D`/`Tiger1D`,
`normalization` = `FrequentistQuantile`, etc.): that is for TIGER's own model sweep
outputs, not the input data.

### Two copies of tiger-main: which to use

```
tiger-main/tiger_full/     upstream repo + data-processed/ + hugging_face/ submodule
tiger-main/tiger-main/     the same, plus Windows setup work:
                             install.bat, install_with_venv.bat, test_installation.py
                             QUICK_START.md, INSTALLATION_GUIDE.md
                             reimplementation_guide.md, CODE_FLOW_GUIDE.md
                             tiger_env/   (a built venv, do not commit)
```

**Use `tiger-main/tiger-main/` for running anything**: it has the working Windows
install. Use `tiger_full/` as the clean upstream reference. They should be consolidated;
see `05_next_steps.md`.

Requires **Python 3.9 + TensorFlow 2.11** (not 3.11). Model weights arrive through the
`hugging_face` **Git LFS** submodule, clone `--recursive` and have Git LFS installed, or
the weights will be silently absent.

Also present: `predictions (other models)/` holds Wei 2021 and Cheng 2023 (DeepCas13)
predictions for the 16 HEK293 genes, collected from their web portals, useful if you want
to reproduce the published model comparison.

---

## 2. Konermann 2023 (Cas13d orthologs)

Files prefixed `[Konermann 2023]` in `URECA_Code/`, plus the paper PDF.

| File | Contents |
|---|---|
| `Cas13d ortholog sequences.csv` | **52 Cas13d ortholog protein sequences**: `Name`, `Sequence`, `Sequence Length`. Source of the CasRx (967 aa) and DjCas13d (877 aa) sequences used in all complexes. |
| `Processed CasRx survival screen data ... after off target filtering.csv` | 65,533 guides, `Guide spacer` (30 nt), `Gene`, `Transcript id`, `Target position`, `Ratio (d14/input)` |
| `The CasRx survival screen raw data, with the guide sequence and day 14input ratio.csv` | unfiltered version of the above |
| `Processed CasRx validation screen data.csv` | 2,293 guides, CD58 and CD81 `bin1/(bin1+4)` flow-cytometry ratios |
| `Individual guide sequences.xlsx` | individually-validated guides |
| `Raw data for individual guide knockdown efficiency and survival rate.xlsx` | per-guide knockdown + survival |

**Activity convention, important.** Konermann activity is expressed as *relative
expression* / *surviving ratio*, so **lower = more active**: the opposite of TIGER's LFC
in sign terms but same direction in meaning. The analysis scripts negate it:
`04_analyze.py` treats `konermann_*` as `mean_rel_expr` **negated**, so that higher always
means more active. Get this wrong and correlations flip sign.

Note spacers here are **30 nt**, versus TIGER's 23 nt. Trim consistently when comparing.

**This file is the key asset for the unrun ProGen3 experiment**: 52 orthologs with known
functional status is exactly the input a protein language model needs.

---

## 3. Azimuth V1 (SpCas9: out-of-domain control)

`Azimuth-master/`, with `azimuth_V1.xlsx` expected in the NSCC data dir. 882 SpCas9 guides
with `mean_screen_activity` (**higher = more active**, used as-is). Subsampled to 500
(full analysis) and 85 (balanced analysis).

Purpose: confirm the null result is not specific to Cas13. It is a different nuclease, a
different nucleic acid (DNA), and a different mechanism, so if structural confidence
predicted activity there but not for Cas13d, that would be informative. It did not.

---

## 4. Nucleaseq

`[Nucleaseq] Supplemental_File_1.xlsx`, high-throughput SpCas9 cleavage kinetics.
**Present but unused.** A possible source of quantitative cleavage-rate labels if the
project moves toward kinetics rather than screen readouts.

---

## 5. Dataset identifiers used in the analysis code

These strings appear throughout `generate_yamls.py` and the analysis outputs:

| ID | Source | Cas protein | Activity column | Direction |
|---|---|---|---|---|
| `tiger_fc` | TIGER `flow-cytometry.bz2` | CasRx | `mean_lfc` | as-is |
| `tiger_ht` | TIGER `hap-titration.bz2` | CasRx | `mean_lfc` | as-is |
| `konermann_casrx` | Konermann | CasRx | `mean_rel_expr` | **negated** |
| `konermann_djcas13d` | Konermann | DjCas13d | `mean_rel_expr` | **negated** |
| `azimuth_v1` | Azimuth | SpCas9 | `mean_screen_activity` | as-is |

---

## 6. Sampling design (and why it was redone)

**First pass (`correlation_results/`):** convenience samples, `tiger_fc` 500,
`tiger_ht` 200, `konermann_casrx` 96, `azimuth_v1` 500. Problem: three of four datasets
use CasRx, so "dataset" and "protein" were confounded, and the unequal *n* made the
p-values incomparable across rows.

**Second pass (`correlation_results/balanced/`):** one dataset per **Cas protein**, 85
guides each, 85 being the DjCas13d ceiling. `tiger_fc` → CasRx,
`konermann_djcas13d` → DjCas13d, `azimuth_v1` → SpCas9. `tiger_ht` and `konermann_casrx`
were dropped as redundant (same protein as `tiger_fc`). Seed fixed at 42 in
`generate_yamls.py`.

The balanced design is the one to trust and to extend. Its weakness is *n* = 85 per
protein: adequate to rule out a strong effect, underpowered for a weak one.
