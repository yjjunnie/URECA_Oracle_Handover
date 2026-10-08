# 04 — Results

The main scientific output of the project. **Read this before running any new
structure-prediction experiment**, so you do not repeat a settled null result.

---

## Headline

> Structural confidence from AlphaFold3 and Boltz-2 does **not** predict Cas13d guide RNA
> activity. Cheap RNA secondary-structure features — particularly target-site
> accessibility — predict it better, and the structural models add nothing on top of them.

---

## 1. AlphaFold3 — 500 CasRx complexes vs TIGER LFC

Source: `alphafold3/my_parts/results/results/correlations.csv`.
Complexes are chain A = CasRx (967 aa), B = crRNA (30 nt DR + 23 nt spacer), C = target RNA.

### AF3 confidence metrics (n = 500)

| Metric | Spearman ρ | p |
|---|---|---|
| `ptm` | −0.002 | 0.97 |
| `iptm` | 0.045 | 0.31 |
| `ranking_score` | 0.046 | 0.31 |
| `mean_plddt` | −0.008 | 0.85 |
| `plddt_chain_A` (protein) | −0.019 | 0.67 |
| `plddt_chain_B` (crRNA) | 0.066 | 0.14 |
| `plddt_chain_C` (target) | 0.023 | 0.61 |
| `iptm_AB` (protein–crRNA) | 0.048 | 0.28 |
| `iptm_AC` (protein–target) | 0.041 | 0.36 |
| `iptm_BC` (crRNA–target) | −0.001 | 0.97 |
| `chain_ptm_B` | 0.086 | 0.055 |

**Every metric is indistinguishable from zero.** Not one reaches significance. `chain_ptm_B`
at p = 0.055 is the closest, and with 13 metrics tested that is expected by chance alone.

### Thermodynamic baselines (same 500 guides)

| Baseline | Spearman ρ | p |
|---|---|---|
| **`log_unpaired`** (target-site accessibility) | **−0.234** | **1.2 × 10⁻⁷** |
| **`hybrid_mfe_1_23`** (guide:target hybridisation energy) | **−0.158** | **3.9 × 10⁻⁴** |
| `mfe` (target MFE alone) | 0.009 | 0.84 |

The baselines are **3–5× stronger** than the best AF3 metric and overwhelmingly
significant. Note `mfe` alone is useless — it is specifically **accessibility of the target
site** and **hybridisation strength** that matter, not global folding energy.

### Partial correlations — does AF3 add anything?

Source: `partial_correlations.csv`. AF3 metrics after controlling for each baseline:

| AF3 metric | controlling for | partial r | p |
|---|---|---|---|
| `ptm` | `log_unpaired` | 0.004 | 0.93 |
| `iptm` | `log_unpaired` | 0.043 | 0.34 |
| `ranking_score` | `log_unpaired` | 0.044 | 0.33 |
| `mean_plddt` | `log_unpaired` | −0.008 | 0.86 |
| `iptm_AB` | `hybrid_mfe_1_23` | 0.030 | 0.51 |

**No incremental signal whatsoever.** AF3 is not capturing a weak version of the
thermodynamic story — it is capturing nothing.

### The pLDDT problem

From `af3_lfc_merged.csv`, absolute confidence is very low across the board:

- `mean_plddt` ≈ **29–31** on every complex
- protein chain A ≈ 31–33, crRNA chain B ≈ 18–22, target chain C ≈ 13–23
- `ptm` ≈ 0.17–0.22, `iptm` ≈ 0.17–0.37

**AF3 is not confident about any of these structures.** A pLDDT of ~30 means
"essentially unmodelled". So the null result has two readings:

1. Structural confidence genuinely does not track guide activity, or
2. AF3 cannot model Cas13d ternary complexes well enough for the question to be asked.

**Interpretation (2) is more likely**, and matters for how you read this. The variance in
ipTM across guides may be noise in a regime where the model has no real structural
understanding — the single-stranded target RNA in particular is near-unmodellable. A
replication with a model that is actually confident on these complexes would still be
worth doing; see `05_next_steps.md`. The low absolute confidence is also consistent with
the independent ESMFold pLDDT anomaly, which is why resolving that diagnostic matters.

Example structures from the activity extremes are kept in
`results/cif_files/top_ranked/` (RPL6, RPL3, FBL, SKIV2L2, COPA) and
`bottom_ranked/` (TRMT6, ACO2, AHCY, PSMB3, MVK) for visual inspection — a useful sanity
check on whether the complexes look remotely plausible.

---

## 2. Boltz-2 — first pass (unbalanced)

Source: `boltz/correlation_results/correlations.csv` →
[`../results/boltz/correlations.csv`](../results/boltz/correlations.csv).
1,296 guides. **The complete 12 metrics × 4 datasets matrix, Spearman ρ:**

| Metric | `tiger_fc` (CasRx, n=500) | `tiger_ht` (CasRx, n=200) | `konermann_casrx` (n=96) | `azimuth_v1` (SpCas9, n=500) |
|---|---|---|---|---|
| `confidence_score` | −0.003 | 0.080 | −0.041 | 0.037 |
| `ptm` | 0.087 | −0.043 | −0.024 | 0.064 |
| `iptm` | 0.045 | −0.023 | −0.140 | 0.039 |
| `complex_plddt` | −0.060 | 0.092 | 0.011 | 0.033 |
| `complex_iplddt` | −0.037 | 0.070 | 0.030 | 0.046 |
| `complex_pde` | −0.042 | −0.048 | 0.127 | 0.001 |
| `complex_ipde` | −0.028 | −0.067 | 0.128 | 0.004 |
| `ptm_grna` | **0.125** | −0.064 | 0.027 | 0.060 |
| `ptm_target` | 0.090 | −0.058 | −0.083 | **0.094** |
| `iptm_prot_grna` | 0.056 | −0.002 | −0.111 | 0.019 |
| `iptm_grna_target` | **0.127** | −0.067 | −0.041 | 0.084 |
| `iptm_prot_target` | 0.043 | −0.033 | **−0.175** | 0.031 |

Bold = the largest |ρ| in that column. Nothing exceeds |ρ| = 0.175, and **only 4 of 48
tests reach p < 0.05** — about what 48 tests produce by chance. All four come from the
large-*n* datasets (`tiger_fc` ×3, `azimuth_v1` ×1), which is a power artifact, not a
signal: `konermann_casrx` has the single largest ρ in the table (−0.175) and is *not*
significant purely because n = 96.

Note the signs are inconsistent across datasets for the same metric (`complex_plddt`:
−0.060, +0.092, +0.011, +0.033). A real effect would point the same way in every column.

Caveat: this pass confounds dataset with protein (three of four are CasRx) and has unequal
*n*, which is why it was redone.

---

## 3. Boltz-2 — balanced re-analysis (the trustworthy one)

Source: `boltz/correlation_results/balanced/correlations_balanced.csv` →
[`../results/boltz/balanced/`](../results/boltz/balanced/).
One dataset per Cas protein, **n = 85 each**, 36 tests. **Complete matrix, Spearman ρ:**

| Metric | `tiger_fc` (CasRx) | `konermann_djcas13d` (DjCas13d) | `azimuth_v1` (SpCas9) |
|---|---|---|---|
| `confidence_score` | −0.007 | **−0.168** | −0.089 |
| `ptm` | 0.041 | −0.031 | 0.021 |
| `iptm` | 0.056 | −0.067 | 0.034 |
| `complex_plddt` | −0.110 | −0.072 | **−0.095** |
| `complex_iplddt` | −0.080 | −0.021 | −0.076 |
| `complex_pde` | 0.025 | −0.003 | −0.008 |
| `complex_ipde` | −0.058 | 0.070 | −0.024 |
| `ptm_grna` | −0.009 | −0.079 | 0.071 |
| `ptm_target` | **−0.116** | 0.113 | 0.084 |
| `iptm_prot_grna` | 0.065 | −0.065 | 0.026 |
| `iptm_grna_target` | 0.063 | −0.059 | 0.011 |
| `iptm_prot_target` | −0.001 | −0.045 | 0.031 |

Largest |ρ| anywhere: **0.168** (`konermann_djcas13d` / `confidence_score`, p = 0.12).

**Not a single significant correlation across all 36 tests.** The marginal `tiger_fc`
signals from the unbalanced pass **did not replicate** — and note `ptm_target` even flips
sign (+0.090 → −0.116), which is the signature of noise rather than a weak true effect.

Two independent structure predictors, three Cas proteins, two nucleic-acid chemistries,
~1,800 complexes in total: **the hypothesis is not supported.**

---

## 4. Secondary findings

**Negative result generalises beyond Cas13.** SpCas9 (`azimuth_v1`) behaves identically.
This is not a Cas13d-specific modelling gap.

**Target accessibility is the real signal.** `log_unpaired` (ρ = −0.234) is the single best
individual predictor found. It is consistent with the mechanism: the guide must access a
target site that is not already base-paired. This is also what TIGER's own feature set
emphasises, and it reinforces the LinearFold-family approach over the structure-prediction
approach for this task.

**Interface metrics are no better than global ones.** The decomposed per-chain and
per-interface metrics (`iptm_prot_grna`, `iptm_grna_target`, `ptm_target`, …) were added
specifically on the theory that a global score dilutes the relevant interface. They did
not help — which further suggests the models lack genuine structural understanding here
rather than that the readout was mis-targeted.

**Boltz-2 is the better platform for future work.** Same null answer as AF3 at a fraction
of the setup cost: `pip install`, no weight request, no container, no genetic databases.
Use it for any follow-up.

---

## 5. Artifacts

All the small analysis outputs below are also copied into
[`../results/`](../results/), so they are available without the working tree.

| Path | Contents |
|---|---|
| `alphafold3/my_parts/results/results/af3_lfc_merged.csv` | per-guide AF3 metrics + LFC + quintile + baselines |
| `.../correlations.csv`, `.../partial_correlations.csv` | AF3 statistics |
| `.../af3_lfc_correlations.png` | AF3 scatter plots |
| `alphafold3/my_parts/results/cif_files/` | top/bottom-ranked structures (.cif + renders) |
| `boltz/correlation_results/boltz_confidence_scores.csv` | per-guide Boltz metrics, all datasets |
| `boltz/correlation_results/correlations.csv` | Boltz statistics, unbalanced |
| `boltz/correlation_results/correlation_heatmap.png` | ρ heatmap, datasets × metrics |
| `boltz/correlation_results/scatter_iptm_prot_target.png` | best-metric scatter |
| `boltz/correlation_results/balanced/*` | the balanced re-analysis (4 files) |
| `boltz/BLAST CasRxd.png` | SMARTBLAST sequence-provenance check (see §4.1 below) |

### 4.1 Sequence provenance check (Boltz)

`boltz/BLAST CasRxd.png` → [`../results/boltz/BLAST_CasRx_smartblast.png`](../results/boltz/BLAST_CasRx_smartblast.png).

A SMARTBLAST of the CasRx sequence used in the complexes, confirming it is the right
protein before 1,296 GPU jobs were spent on it:

- **100% identity, 100% query cover, E = 9e−20** to *type VI-D CRISPR-associated
  RNA-guided ribonuclease Cas13d* [*Ruminococcus* sp. XPD3002] — `WP_075424065.1`
- 97.92% to the same protein from *Ruminococcus* sp. — `MBR6985772.1`
- 100% to **PDB `9M31_A` (chain A, CasRx)** and **`9LZT_B` (chain B, RfxCas13d)**

Two things follow. First, the sequence is confirmed correct, so the null result is not a
wrong-protein artifact. Second — and more useful — **`9M31` and `9LZT` are experimental
structures of this exact protein.** They are the ready-made ground truth for the
"are these complexes modellable at all?" question in `05_next_steps.md` §2.2.

---

## 6. How to report this

This is publishable as a negative result, and is more useful stated precisely than vaguely:

> Across ~1,800 predicted Cas13d and SpCas9 ternary complexes from two independent
> AF3-class structure predictors (AlphaFold3, Boltz-2), no structural confidence metric —
> global, per-chain, or per-interface — correlated with measured guide RNA activity
> (all |ρ| < 0.18; no significant result in a protein-balanced design, n = 85 per
> protein). RNA secondary-structure baselines on the same guides were substantially
> stronger (target-site accessibility, ρ = −0.234, p = 1.2 × 10⁻⁷), and partial
> correlation showed the structural metrics contributed no information beyond them.
> Predicted complex confidence was uniformly low (mean pLDDT ≈ 30), indicating current
> structure predictors do not model Cas13d:crRNA:target ternary complexes at a fidelity
> that supports activity prediction.

State the pLDDT ≈ 30 caveat explicitly — it is the difference between "confidence does not
predict activity" (a strong claim this data does not fully support) and "these models
cannot yet model these complexes" (what the data actually shows).
