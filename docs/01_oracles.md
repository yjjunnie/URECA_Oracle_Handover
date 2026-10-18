# 01: The Oracle Models

An "oracle" here means a pretrained model used off-the-shelf to score guide RNAs,
without training it on knockdown data.

Each section gives: **what it is → published performance → how it was run here → outcome**.

---

## 1. AlphaFold3

**What it is.** DeepMind's biomolecular structure predictor. Unlike AF2 it handles
protein–nucleic-acid complexes, which is why it was the first choice: a Cas13d complex is
protein + crRNA + target RNA.

**Why it was tried.** Hypothesis: a guide that genuinely engages the target will produce a
confidently-predicted ternary complex, so ipTM / pLDDT should correlate with knockdown.

**How it was run.** Source in `alphafold3/`; all project work in `alphafold3/my_parts/`.
Run on NSCC ASPIRE via Singularity (`alphafold3.sif`), as a 4-stage PBS pipeline:

| Stage | Script | Function |
|---|---|---|
| 0 | `00_decompress_weights.pbs` | unpack `af3.bin.zst` model parameters |
| 1 | `01_fill_casrx.pbs` + `fill_casrx_sequence.py` | insert the full 967 aa CasRx sequence into every input JSON |
| 2 | `02_af3_msa.pbs` | MSA/data pipeline stage (CPU-heavy, genetic DB search) |
| 3 | `03_af3_inference_batched.pbs` | GPU inference, **PBS array job**, 10 complexes/task, `-J 0-49%10` |
| 3b/3c | `03b_..._custom_msa.pbs`, `03c_..._native.pbs` | variants: hand-built MSA, and a native (non-container) install |
| 4 | `04_analyze.pbs` + `analyze_af3_results.py` | parse confidences, correlate against TIGER LFC |

Complex layout: **chain A** = CasRx protein, **chain B** = crRNA (30 nt direct repeat +
23 nt spacer), **chain C** = target RNA.

Notable implementation details worth knowing:
- AF3 would not find pre-computed `_data.json` files when given `--input_dir`, so
  `03_af3_inference_batched.pbs` loops and calls AF3 **once per JSON** with `--output_dir`
  pointed at that job's own MSA subdirectory. Keep this if you re-run.
- A CasRx-specific MSA was built by hand (`build_casrx_msa.py` → `casrx_orthologs.a3m`)
  because the standard pipeline MSA was weak for Cas13d.
- `fix_rna_pairedmsa.py` patches an RNA paired-MSA format issue.
- `reorganise_batches.py` shards inputs into `batch_00 … batch_49`.

**Outcome.** 500 complexes completed. **No metric predicted activity**: all |Spearman ρ|
< 0.09 and non-significant; thermodynamic baselines were ~3× stronger. Full numbers in
`04_results.md`. Statistics copied into
[`../results/alphafold3/`](../results/alphafold3/); representative structures kept in
`my_parts/results/cif_files/{top_ranked,bottom_ranked}/`.

**Weights/databases.** Not in git, and must not be committed, the parameters may not be
shared outside the organisation. They download directly from
https://storage.googleapis.com/alphafold3/af3.bin.zst (no request form); genetic databases
via `alphafold3/fetch_databases.sh`. Terms and their consequences for this project:
[`06_script_legend.md` §9.2.1](06_script_legend.md#921-alphafold3-weights-download-is-open-sharing-is-not).

---

## 2. Boltz-2

**What it is.** An open MIT-licensed AF3-class structure predictor. Chosen as the
replacement for AF3 because it installs with `pip install boltz`, needs no weight request,
and is far faster to iterate on.

**How it was run.** Everything in `boltz/`, a 6-stage pipeline:

| Script | Function |
|---|---|
| `00_install_boltz.pbs` | Python 3.11 venv in scratch, `pip install boltz`, extract `mols.tar` |
| `01_test_boltz.pbs` | GPU smoke test on a minimal CasRx complex; **prints the confidence-JSON keys**, which you need before writing any parser |
| `02_fix_torch_cuda.pbs` | reinstall torch against the node's actual CUDA if `torch.cuda.is_available()` is False |
| `generate_yamls.py` / `.pbs` | build one input YAML per guide + a `manifest.tsv` (guide_id / yaml_path / activity) |
| `03_boltz_batch.pbs` | **PBS array job**, 20 guides per task, `-J 0-64` |
| `04_analyze.py` + `05_analyze.pbs` | parse confidence JSONs, Spearman/Pearson per dataset × metric, heatmap, scatter |
| `04b_analyze_balanced.py` + `05b_...pbs` | protein-balanced re-analysis (85 guides per Cas protein) |
| `upload_to_hf.py`, `download_from_hf.py`, `05/06_upload_results.pbs` | move results via Hugging Face, since scratch is purged |

Input YAML is simply three sequences; see `templates/boltz_input.yaml`.

Metrics extracted (12): `confidence_score`, `ptm`, `iptm`, `complex_plddt`,
`complex_iplddt`, `complex_pde`, `complex_ipde`, `ptm_grna`, `ptm_target`,
`iptm_prot_grna`, `iptm_grna_target`, `iptm_prot_target`.

**Outcome.** Run across 4 datasets (1,296 guides total), then re-run protein-balanced.
**Same null result as AF3**: best |ρ| = 0.175, and **0 of 36 balanced tests significant**.
Full matrices in `04_results.md` §2–3. Results in `boltz/correlation_results/`, copied into
[`../results/boltz/`](../results/boltz/).

**Two supporting Boltz artifacts, easy to miss:**

- **`Boltz Inference Guide.ipynb`** (in the parent folder, not `boltz/`), an 18-cell
  methods notebook written while porting the AF3 experiment to Boltz. **It has no executed
  outputs: it is a design document, not a results notebook.** Contents worth keeping:
  an AF3-vs-Boltz difference table (JSON/`dialect: alphafold3` vs YAML, RNA handling, MSA),
  the DjCas13d sequence lookup, spacer→target reverse-complement derivation, the
  SpCas9/Azimuth `30mer` parsing rule (protospacer = positions `[4:24]`) and sgRNA
  scaffold, the direct-repeat sequences per ortholog, and the output-parsing layout.
  Read it before modifying `generate_yamls.py`.
- **`boltz/BLAST CasRxd.png`**: SMARTBLAST confirming the CasRx sequence is genuinely
  type VI-D Cas13d (100% identity) and matches PDB `9M31_A` / `9LZT_B`. See
  `04_results.md` §4.1; those PDB entries matter for future work.

**Where the results actually live.** Scratch was purged, so the canonical store is a
**private Hugging Face dataset repo, `yjjunnie/ureca-boltz-data`**, holding
`results_fullprot/` and `results_balanced/` (plus `data/` and `scripts/`).
`06_upload_results.pbs` pushes there; `download_results_from_hf.py` pulls back.

On disk, the two prefixes landed as:

| HF prefix | Local path |
|---|---|
| `results_fullprot/` | `boltz/correlation_results/` |
| `results_balanced/` | **`boltz/correlation_results/balanced/`** |

Both are copied into [`../results/boltz/`](../results/boltz/) and
[`../results/boltz/balanced/`](../results/boltz/balanced/), 4 files each, matching the 4
outputs `04_analyze.py` and `04b_analyze_balanced.py` each declare, so the handover is
complete without needing repo access.

**The download script's path mapping does not match the layout above.**
`download_results_from_hf.py` sets `DEST_DIRS["results_balanced"]` to
`correlation_results_balanced/` (a sibling), not `correlation_results/balanced/` (a
subdirectory). Re-running it as written will create a second, parallel directory instead of
refreshing the balanced results in place. Fix the mapping before re-running:

```python
DEST_DIRS = {
    "results_fullprot": os.path.join(BASE, "correlation_results"),
    "results_balanced": os.path.join(BASE, "correlation_results", "balanced"),
}
```

`download_results_from_hf.py` and `upload_to_hf.py` contain a **hardcoded Hugging Face
token**. It was deliberately not copied into this repo. See `05_next_steps.md` → Known debts.

**Weights.** `boltz2_conf.ckpt` (2.29 GB) and `mols.tar` (1.86 GB) were transferred to
NSCC manually by `scp -O`; they are *not* auto-downloaded in this setup because compute
nodes have no outbound internet. They live in the parent folder locally; re-obtainable
from the Boltz release assets.

---

## 3. ESMFold

**What it is.** Meta's single-sequence structure predictor (ESM-2 language model + folding
head). No MSA needed, so it is fast.

**Why it was tried.** Intended as a cheap screen for whether a **Cas13 ortholog protein**
is plausibly well-folded/functional, a protein-level rather than guide-level oracle.

**Published performance** (from the annex slides): TM-score 0.83 on CAMEO and 0.68 on
CASP14, versus ~0.37–0.47 for AF2/RoseTTAFold without MSAs. pLDDT correlates with true
LDDT at r = 0.85, and the gap to AF2 shrinks as pLDDT rises (r = −0.79), i.e. **ESMFold is
usually right when it is confident**, which is exactly the property needed for a filter.

**How it was run.** `esmfold_test/00_diagnose_plddt.{py,pbs}`.

**Status: this is an open blocker.** The pipeline reported an average pLDDT of ~30 on
*natural* sequences, which is implausibly low and indicates a pipeline fault rather than
biology. The diagnostic script was written to settle it: it folds reference proteins with
known expected confidence (ubiquitin, GB1 → expect ~85–95; α-synuclein → genuinely
disordered, ~25–40) and prints four candidate pLDDT aggregations side by side:

- **A** `out["mean_plddt"]`, the correct atom-masked value
- **B** `out["plddt"].mean()`, naive mean over all 37 atom slots including non-existent ones
- **C** CA-only per-residue mean
- **D** B-factor column mean from `output_to_pdb()`

Each sequence is folded twice, alone and inside a mixed-length batch, to expose padding
contamination. Interpretation: if ubiquitin gives A ≈ 90, the pipeline is fine and the "30"
came from reading B/C/D; if ubiquitin also gives A ≈ 30, the weights/dtype/truncation are
broken and nothing downstream is meaningful.

**There is no results file in `esmfold_test/`, so this diagnostic appears never to have
been run to conclusion.** It is a cheap, high-value first task; see `05_next_steps.md`.

---

## 4. ProGen3

**What it is.** Profluent's protein language model (112M → 46B parameters). Scores a
sequence's log-likelihood and perplexity, a measure of how "natural" a protein is.

**Published performance** (annex slides): on ProteinGym zero-shot substitutions, Spearman
ρ plateaus at **0.35–0.40** around 10²¹ pre-training FLOPs, for the 3B model. ρ measures
rank correlation between the model's log-likelihood and experimentally measured fitness
from deep-mutational-scanning data. Interpretation recorded in the slides: this is low, but
**enough to act as a coarse predictor of whether a sequence is plausible as a protein**:
so it is a screening filter, not a fitness predictor. Note the scaling curve is flat past
3B, so using a bigger checkpoint buys little.

**How it was run.** `progen3-main/`, with project-written NSCC scripts:
`nscc_setup.sh` (conda env, `gcc/11.2.0-nscc` + `cuda/12.2.2`), `nscc_score_job.sh`
(scoring), `nscc_generate_job.sh` (generation). `NSCC_GUIDE.md` is a complete, standalone
walkthrough, worth reading as a model for how to document a cluster workflow.
`SCORER_EXAMPLE.md` gives exact input/output shapes; `demo_scorer.py` runs locally.

Model sizing (from `nscc_score_job.sh`): 112m ≈ 4 GB VRAM, 219m ≈ 8 GB, 339m ≈ 12 GB,
762m ≈ 20 GB, 1b ≈ 30 GB. Pick to fit your allocation.

**Status.** Environment and scripts work; **never applied to the Cas13 ortholog set.** The
obvious experiment, score the Konermann Cas13d orthologs and check whether
log-likelihood separates the functional from the non-functional ones, is unrun.

---

## 5. TIGER (the supervised benchmark)

**What it is.** The state-of-the-art supervised Cas13d guide-efficacy model (Wessels,
Stirn et al., *Nature Biotechnology* 2023; `tiger-main/`). Deep CNN on guide + target
context. Not an oracle: it is the **bar everything else is measured against**, and the
source of the activity labels used throughout.

**Published performance** (annex slides):
- Beats all three prior Cas13d models, Wessels 2020 (RF), Wei 2021, Cheng 2023
  (DeepCas13), on Pearson, Spearman, AUROC and AUPRC.
- Beats them on **both** an essential-gene dropout screen *and* a cell-surface-marker
  screen. The second matters: it comes from a different study, uses flow cytometry rather
  than survival as the readout, and shares no genes, making it a true
  **out-of-distribution generalisation test**, not just a held-out split.
- Genome-wide screens: **AUROC 0.95 (HAP1) and 0.86 (HEK293FT)**.

Two readout types, worth understanding because they define the labels:
- *Essential-gene dropout:* an active guide knocks down a survival-critical gene, the cell
  dies, that guide depletes from the population, so **depletion magnitude = activity**.
- *Cell-surface-marker:* activity read by flow-sorting cells on surface protein level.

**How it was used here.** Local inference on Windows and as the label source. Two copies
exist under `tiger-main/`; see `03_datasets.md` for which to use. Needs **Python 3.9 +
TensorFlow 2.11** (not 3.11); `QUICK_START.md` and `install_with_venv.bat` handle setup.
Model weights come from the Hugging Face submodule via **Git LFS**, so clone with
`--recursive` or the weights will be missing.

**Not done:** TIGER was never retrained, and no oracle score was ever tested as an *extra
input feature* to TIGER. That is the most promising remaining thread.

---

## 6. LinearFold / RNA secondary structure baselines

**What it is.** LinearFold predicts RNA secondary structure in **O(n) time and memory**
using beam search, against the O(n³)/O(n²) of classical algorithms.

**Published performance** (annex slides):
- Runtime scales ~n^1.0–1.2 vs n^2.2–3.0 for Vienna RNAfold and CONTRAfold MFE; memory
  ~n^1.0 vs n^2.0. On a 10⁵ nt sequence this is minutes vs hours.
- **It is also more accurate, not just faster**: overall PPV/sensitivity
  55.84/56.24 (LinearFold-C) vs 54.51/55.36 (CONTRAfold MFE), and 50.51/58.97
  (LinearFold-V) vs 50.22/58.74 (Vienna RNAfold). The gain concentrates in **longer
  families and long-range base pairs**, where exact search is hurt by error accumulation.
- **PPV** = fraction of predicted pairs that are real (are the predictions correct).
  **Sensitivity** = fraction of real pairs that were predicted (did it find them).
- `-V` vs `-C` is only the beam-search scoring function: **-V** = Vienna thermodynamic
  free-energy model, **-C** = CONTRAfold's machine-learned model.

**How it was used.** As thermodynamic baseline features in the AF3 analysis:
`mfe` (target MFE), `hybrid_mfe_1_23` (guide:target hybridisation energy over the 23 nt
spacer), and `log_unpaired` (log probability the target site is unpaired/accessible).

**Outcome: this is the surprise.** These cheap features were the **only** things that
predicted activity: `log_unpaired` ρ = −0.234 (p = 1.2e−7) and `hybrid_mfe_1_23`
ρ = −0.158 (p = 3.9e−4), both far ahead of every deep structural metric. Partial
correlation showed AF3 adds **nothing** on top of them. Target-site accessibility is
doing the work.

---

## 7. Azimuth

**What it is.** The Doench/Fusi SpCas9 **on-target** efficiency model (`Azimuth-master/`),
a gradient-boosted regressor on 30-mer sequence features. A DNA-cutting, not RNA-targeting,
model.

**How it was used.** Only as a **negative/out-of-domain control dataset** in the Boltz
analysis (`azimuth_v1`, 882 guides, subsampled to 85/500). SpCas9 complexes were folded
and correlated the same way. As expected, structural confidence did not predict SpCas9
activity either, which usefully shows the null result is not Cas13-specific.

---

## 8. Cas13 background (for context)

From the annex slides, the biology the complexes model:

Cas13 is CRISPR **type VI**: RNA-guided *RNA*-targeting. The effector has two lobes:
- **REC (recognition)** lobe: N-terminal (NTD) + helical-1 domains, mainly **crRNA recognition**.
- **NUC (nuclease)** lobe: helical-2 plus **split HEPN-1 and HEPN-2** domains, mainly
  **target RNA accommodation and cleavage**. The HEPN pair is the catalytic site.
- Extra domains: helical-3 (linker) in type VI-A; RRI (lid) in type VI-B.

Subtypes and effector sizes: VI-A `cas13a` ~1,200 aa; VI-D `cas13d` ~930 aa (this is
**CasRx/RfxCas13d**, the project's main protein, 967 aa); VI-C `cas13c` ~1,100 aa;
VI-CT `cas13ct` ~800 aa; VI-B1/B2 `cas13b1/b2` ~1,100 aa; VI-BT `cas13bt` (cas13x/cas13y)
~800 aa. VI-A and VI-D loci carry `cas1`/`cas2` adaptation genes; ancillary genes include
`WYL1` (VI-D), `csx27` and `csx28` (VI-B).

Cas13d's small size (~930 aa) is why it is the practical choice for delivery, and why it
is the focus here. The other protein used was **DjCas13d** (877 aa); **SpCas9** (1,368 aa)
served as the out-of-domain control.
