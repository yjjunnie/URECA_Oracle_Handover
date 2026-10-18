# 06 — Script Legend and NSCC Run Guide

A complete index of every script in [`../code/`](../code/), what it is for, which model it
belongs to, and where it runs. Also covers what is **not** in this repository and must be
downloaded manually.

Written for a reader who has not encountered these models before. Each model gets a
one-paragraph introduction before its script table.

- Cluster terminology: [`../code/README.md` §1](../code/README.md#1-cluster-vocabulary).
- PBS mechanics in depth: [`02_nscc_job_scripts.md`](02_nscc_job_scripts.md).
- Per-model scientific detail and outcomes: [`01_oracles.md`](01_oracles.md).

---

## 1. Running a script on NSCC

The same seven steps apply to every job script in this repository.

| Step | Action | Command |
|---|---|---|
| 1 | Log in to the login node. | `ssh <YOUR_NSCC_ID>@aspire2a.nus.edu.sg` |
| 2 | Substitute the two placeholders in the scripts. | See [`../code/README.md` §2](../code/README.md#2-replace-the-placeholders-first) |
| 3 | Create the log directory, or jobs fail silently. | `mkdir -p /scratch/users/ntu/<YOUR_NSCC_ID>/logs` |
| 4 | Confirm the script's resource line matches the need (GPU vs CPU). | `grep '#PBS -l' script.pbs` |
| 5 | Submit. | `qsub script.pbs` |
| 6 | Monitor. | `qstat -u <YOUR_NSCC_ID>` |
| 7 | Read the logs once finished. | `cat /scratch/users/ntu/<YOUR_NSCC_ID>/logs/<name>.out` |

Additional notes:

- **Array jobs** (`#PBS -J 0-49`) are submitted exactly the same way. A single `qsub`
  creates all tasks.
- **`qdel <jobid>`** cancels a job. For an array job, `qdel <jobid>[]` cancels all tasks.
- **Walltime overruns kill the job with no output.** Pad every estimate.
- **Scratch is wiped periodically.** Upload results at the end of each pipeline, never
  later.

### 1.1 Where each script must run

The "Runs on" column in the tables below uses these values.

| Value | Meaning | Why it matters |
|---|---|---|
| **GPU node** | `#PBS -l select=...:ngpus=1`, submitted with `qsub` | Requesting no GPU makes the model fall back to CPU and run orders of magnitude slower, or crash. |
| **CPU node** | `#PBS -l select=...` with no `ngpus`, submitted with `qsub` | Requesting a GPU for these wastes allocation; queue times are also longer. |
| **Login node** | Run directly, not submitted | Compute nodes have **no outbound internet**. Anything that downloads or uploads must run here. |
| **Local (Windows)** | Run on a personal machine | TIGER and the result-retrieval scripts were run locally, not on the cluster. |

---

## 2. Boltz-2 — the pipeline to copy

**What the model is.** Boltz-2 is an open-source biomolecular structure predictor,
comparable in scope to AlphaFold3: given the sequences of a protein and any nucleic acids
bound to it, it predicts the 3D structure of the assembled complex and reports confidence
scores for its own prediction. It is installable from PyPI with no weight request, which is
why it carried the bulk of this project.

**Why it was used here.** The project tested whether the model's *confidence* in a
Cas13d:crRNA:target complex predicts how well that guide RNA actually works in cells.

**Status.** Complete. 1,296 complexes across 4 datasets, plus a protein-balanced re-run.
This is the valid portion of the project's negative result.

Run the numbered scripts in order.

| Order | Script | Type | Runs on | Purpose |
|---|---|---|---|---|
| — | `download_from_hf.py` | Python | **Login node** | Downloads the input datasets and script copies from the Hugging Face dataset repo onto NSCC. Run before anything else. |
| — | `download_from_hf.pbs` | PBS | CPU node | Job-script wrapper for the above. **Will fail** — compute nodes cannot reach Hugging Face. Use the `.py` on the login node instead. |
| 00 | `00_install_boltz.pbs` | PBS | CPU node | Builds the Python environment and unpacks the ligand cache. CPU-only by design: installation takes 30+ minutes and does not need a GPU. Safe to re-run; skips completed work. |
| 01 | `01_test_boltz.pbs` | PBS | GPU node | Folds one small complex as a smoke test. **Do not skip.** It prints the key names in the output JSON, which are required before any parser can be written. Guessing them and re-running 1,300 GPU jobs is the error this prevents. |
| 02 | `02_fix_torch_cuda.pbs` | PBS | CPU node | Only needed if `torch.cuda.is_available()` returns `False`. Reinstalls PyTorch against the CUDA version the node actually provides. Set `CUDA_TAG` to match `nvidia-smi`. |
| 02a | `generate_yamls.py` | Python | CPU node | Builds one Boltz input YAML per guide RNA, plus a `manifest.tsv` indexing them. Its final line prints the exact `#PBS -J` range for the next step — use that rather than counting by hand. |
| 02b | `generate_yamls.pbs` | PBS | CPU node | Job-script wrapper for `generate_yamls.py`. |
| 03 | `03_boltz_batch.pbs` | PBS | **GPU node**, array `0-64` | The inference stage, and the expensive one. 20 guides per task. Each task copies its inputs to a private folder first so parallel tasks do not collide. |
| 04 | `04_analyze.py` | Python | CPU node | Parses the confidence JSONs, correlates every confidence metric against measured guide activity, writes CSVs and plots. |
| 05 | `05_analyze.pbs` | PBS | CPU node | Runs `04_analyze.py` in a lightweight CPU environment. |
| 04b | `04b_analyze_balanced.py` | Python | CPU node | The same analysis, subsampled to 85 guides per Cas protein. **This is the authoritative version** — the unbalanced analysis confounds dataset with protein. |
| 05b | `05b_analyze_balanced.pbs` | PBS | CPU node | Runs `04b_analyze_balanced.py`. |
| 06 | `06_upload_results.pbs` + `upload_to_hf.py` | PBS + Python | See note | Pushes results to Hugging Face. Run as the **final stage of every pipeline**, because scratch is wiped. This is submitted as a PBS job but needs outbound internet, which contradicts the rule above. Verify it can reach Hugging Face before relying on it; if not, run `upload_to_hf.py` from the login node. |
| — | `download_results_from_hf.py` | Python | Local (Windows) | Pulls finished results back to a personal machine. **Has a known unfixed bug** — see [`../code/README.md` §4.4](../code/README.md#44-known-unfixed-bug). |
| — | `Boltz_Inference_Guide.ipynb` | Notebook | Reference only | Design notes from porting the AF3 setup to Boltz: the two input formats, reconstructing target sequences from spacers, the Azimuth `30mer` parsing rule, the direct-repeat sequences. **No saved outputs — notes, not results.** Read before modifying `generate_yamls.py`. |

---

## 3. AlphaFold3 — read the warning first

**What the model is.** DeepMind's structure predictor, and the first to handle
protein–nucleic-acid complexes well, which is why it was the project's first choice: a
Cas13d complex is protein + crRNA + target RNA. Unlike Boltz-2, both its code licence and
its weights carry restrictions, though the weights now download directly (§9.2.1).

**Status: the production run here is void.** All 500 complexes were folded with an
**empty protein MSA**, so the protein was never meaningfully folded. The fix is written and
validated on one complex but was never applied at scale. Read
[`../README.md` §2.3](../README.md#23-the-alphafold3-arm-is-invalid) before using anything
in this directory.

**Complex layout used throughout:** chain A = CasRx protein, chain B = crRNA (30 nt direct
repeat + 23 nt spacer), chain C = target RNA.

### 3.1 Setup and input preparation

| Order | Script | Type | Runs on | Purpose |
|---|---|---|---|---|
| — | `install_af3_native.sh` | Shell | CPU node | Installs AF3 natively with conda, bypassing the official Docker route, which needs root. Header comments explain each workaround. Takes 10–30 minutes; run on a compute node, not the login node. |
| 00 | `00_decompress_weights.pbs` | PBS | CPU node | Unpacks the compressed AF3 weights (`af3.bin.zst`) into scratch. Run once, before anything else. |
| 01 | `01_fill_casrx.pbs` + `fill_casrx_sequence.py` | PBS + Python | CPU node | Fetches the 967 aa CasRx sequence from UniProt and substitutes it into every input JSON, which ship with a placeholder. Superseded by `add_msa_to_json.py` for the fixed pipeline. |
| 02 | `02_af3_msa.pbs` | PBS | CPU node, array `0-499` | Runs AF3's own database search to build the MSA. CPU-heavy and does not touch the neural network, so no GPU should be requested. **This is the stage that silently failed.** |
| 02a | `reorganise_batches.py` | Python | Login/CPU node | Shards the 500 input JSONs into 50 folders of 10, so inference can run as a 50-task array job. |

### 3.2 The MSA fix — the chain worth understanding

These three scripts are the project's main technical contribution and the reason the AF3 arm
can be salvaged.

| Script | Type | Purpose |
|---|---|---|
| `build_casrx_msa.py` | Python | Builds a curated alignment from the 52 Cas13d orthologs in the Konermann dataset, instead of relying on AF3's database search to find homologs. Its docstring records the diagnosis of the pLDDT ≈ 30 problem. Output: `casrx_orthologs.a3m`. |
| `add_msa_to_json.py` | Python | Injects the alignment **and** the protein sequence in a single pass. Both together by design: AF3 requires the first alignment sequence to match the chain's `sequence` field exactly, and one step prevents the two drifting apart. Supersedes `fill_casrx_sequence.py`. |
| `fix_rna_pairedmsa.py` | Python | Strips the `pairedMsa` key from RNA chains. It is a protein-only field; older AF3 builds ignored it, current ones raise `ValueError: Unexpected JSON keys`. |

### 3.3 Inference — three routes, only one usable

| Script | Type | Runs on | When to use |
|---|---|---|---|
| `03_af3_inference_batched.pbs` | PBS | GPU node, array `0-49%10` | The original. **Produced the void run.** Retained only as a reference for the array-job batching pattern. |
| `03b_af3_inference_custom_msa.pbs` | PBS | GPU node | The custom-MSA fix via a Singularity container. **The container image no longer exists on scratch**, so this will not run as-is. Retained as a worked container example. |
| **`03c_af3_inference_native.pbs`** | PBS | **GPU node** | **Start here.** Functionally identical to `03b` — same inputs, same outputs — but natively installed rather than containerised. Better preflight: verifies the weights exist, verifies `import alphafold3` works, and prints `jax.devices()` before committing to a run. |

`03b` and `03c` differ only in how AF3 is installed. Use `03c` unless the container image
has been rebuilt.

### 3.4 Analysis

| Script | Type | Runs on | Purpose |
|---|---|---|---|
| `04_analyze.pbs` + `analyze_af3_results.py` | PBS + Python | CPU node | Parses AF3 outputs, correlates confidence against activity, and runs **partial correlations** to test whether AF3 adds anything beyond the simple thermodynamic features. It does not. This is the version that produced the committed results; an unfinished refactor was removed because a column-name mismatch would crash it before plotting. |

---

## 4. ESMFold

**What the model is.** A structure predictor built on the ESM-2 protein language model. It
needs no MSA, inferring structure from a single sequence, which makes it fast but generally
less accurate on hard targets. It handles **protein only** — it cannot fold the RNA chains,
so it was never a candidate for the full complex.

**Status: blocked, and the easiest thing to pick up.** ESMFold was reporting ~30 average
pLDDT on ordinary proteins, which cannot be correct.

| Script | Type | Runs on | Purpose |
|---|---|---|---|
| `00_diagnose_plddt.py` + `.pbs` | Python + PBS | GPU node | **Unfinished diagnostic.** Folds reference proteins of known expected confidence (ubiquitin and GB1 should score 85–95; α-synuclein is genuinely disordered and should score 25–40) and prints four methods of averaging pLDDT side by side. A ubiquitin score near 90 means the pipeline is sound and the wrong statistic was being read; near 30 means a real defect. Each protein is folded alone **and** in a batch, to detect padding contamination. |

Set `TORCH_HOME` to scratch before the first run, or the ~2.6 GB checkpoint lands in the
home directory and exhausts the quota.

---

## 5. ProGen3

**What the model is.** A protein *language* model — it treats amino-acid sequences the way a
text model treats sentences. It does not predict structure. It can score how "plausible" a
protein sequence is under its learned distribution, and it can generate new sequences.

**Why it was intended here.** To screen newly discovered Cas13 orthologs by plausibility,
without any structural prediction.

**Status: set up and working, but never pointed at the Cas13 orthologs.** That experiment is
entirely unrun and self-contained.

| Script | Type | Runs on | Purpose |
|---|---|---|---|
| `nscc_setup.sh` | Shell (PBS header) | **GPU node** | Builds the conda environment. Run once. Must be a GPU job: `grouped_gemm` requires a GPU present at install time. |
| `nscc_score_job.sh` | Shell (PBS header) | GPU node | Scores sequences from a FASTA file. Edit the config block near the top to specify the input. |
| `nscc_generate_job.sh` | Shell (PBS header) | GPU node | Generates new sequences rather than scoring existing ones. |
| `NSCC_GUIDE.md` | Doc | — | A standalone walkthrough: SSH access, setup, submission, monitoring, retrieval. **The best starting point for anyone new to NSCC** — it assumes no prior knowledge. |
| `SCORER_EXAMPLE.md` | Doc | — | Exact input and output shapes, so the format is known in advance. |
| `CODE_FLOW_GUIDE.md` | Doc | — | Structure of the ProGen3 codebase. |

Despite the `.sh` extension, the three `nscc_*.sh` files carry PBS headers and are submitted
with `qsub`, not executed directly.

**GPU memory by model size:** 112m ≈ 4 GB, 219m ≈ 8 GB, 339m ≈ 12 GB, 762m ≈ 20 GB,
1b ≈ 30 GB, 3b ≈ 40 GB (requires an A100). Prefer 3b where available; the published accuracy
curve is flat beyond 3B, so larger models offer no gain.

---

## 6. TIGER — the benchmark

**What the model is.** A supervised deep learning model trained directly on large-scale
Cas13d screens, in which thousands of guide RNAs were tested in cells. It is the current
best guide-activity predictor, and the thing this project was trying to match without
labelled data.

**Role here.** Two roles: the benchmark everything else is measured against, and the
**source of the activity labels** every correlation in this project is computed against.
Never retrained.

Runs locally on Windows, not on NSCC.

| File | Type | Runs on | Purpose |
|---|---|---|---|
| `QUICK_START.md` | Doc | — | **Read first.** Takes the reader from nothing to a working install. |
| `INSTALLATION_GUIDE.md` | Doc | — | Full dependency list with pinned versions, plus troubleshooting. |
| `install_with_venv.bat` | Batch | Local (Windows) | Automated install into a virtual environment. |
| `test_installation.py` | Python | Local (Windows) | Verifies every package imports and reports whether a GPU was found. |
| `DECOMPRESSION.py` | Python | Local (Windows) | Unpacks the `.bz2` datasets. |
| `view_index_structure.py` | Python | Local (Windows) | Inspects the multi-index on the prediction files. |
| `COLUMN_EXPLANATIONS.md` | Doc | — | Definition of every column in the prediction output. Needed to know which column is the activity label. |
| `CODE_FLOW_GUIDE.md` | Doc | — | Structure of the TIGER codebase. |
| `reimplementation_guide.md` | Doc | — | Notes on the model internals, for anyone rebuilding it. |

**TIGER requires Python 3.9 and TensorFlow 2.11.** It will not work on 3.11. Clone with
`git clone --recursive` or the weights, which arrive via a Git LFS submodule, will be
silently absent — producing a working install that cannot predict anything.

---

## 7. Analyses with no scripts, and why

Two components appear in the results but have **no dedicated script**. This is intentional,
and is recorded here so no one goes looking for missing files.

| Component | Why there is no script | Where it actually lives |
|---|---|---|
| **LinearFold / RNAfold thermodynamic baselines** — the project's only positive result | The features were **not computed by this project**. `mfe`, `hybrid_mfe_1_23` and `log_unpaired` arrive as **pre-existing columns in the TIGER dataset**. The analysis scripts read them directly. | Consumed by `alphafold3/analyze_af3_results.py`; columns documented in [`03_datasets.md` §1](03_datasets.md#schema). |
| **Azimuth (SpCas9)** | Used only as an **out-of-domain control dataset**, not as a model that was run. Its guides were folded by the ordinary Boltz pipeline. | Dataset `azimuth_v1`, 882 guides subsampled to 85; see [`03_datasets.md` §3](03_datasets.md#3-azimuth-v1-spcas9--out-of-domain-control). |

Consequence worth understanding: because the strongest predictor in the entire project is a
**column someone else computed**, anyone continuing this work should compute these features
themselves for any new dataset. See [`05_next_steps.md` §3.3](05_next_steps.md#33-linearfold-properly).

---

## 8. Templates

Blank job scripts to copy when writing new ones. Documented in
[`02_nscc_job_scripts.md` §7](02_nscc_job_scripts.md#7-templates).

| Template | Purpose |
|---|---|
| `single_gpu.pbs` | One GPU, one task. **Use this first** to verify the GPU environment works before anything else. |
| `array_job.pbs` | The N-tasks pattern, with the index arithmetic already correct. |
| `cpu_analysis.pbs` | CPU-only, for parsing and plotting stages. |
| `boltz_input.yaml` | A worked Boltz input file, annotated. |

---

## 9. What is not in this repository

Nothing in the three tables below is version-controlled here. All of it must be obtained
separately.

### 9.1 Model code

Clone fresh rather than relying on a vendored copy. Versions used by this project are listed
where pinning matters.

| Model | Source | Version used | Notes |
|---|---|---|---|
| Boltz-2 | `pip install boltz` (PyPI) | June 2025 | No clone needed. |
| AlphaFold3 | https://github.com/google-deepmind/alphafold3 | — | Code only; weights download separately (§9.2). Install notes: [`docs/installation.md`](https://github.com/google-deepmind/alphafold3/blob/main/docs/installation.md) — read before `install_af3_native.sh`. |
| TIGER | https://github.com/daklab/tiger | `NBT-submission` tag | **Clone with `--recursive`.** |
| ProGen3 | https://github.com/profluent-ai/progen3 | 3B checkpoint | — |
| ESM / ESMFold | https://github.com/facebookresearch/esm | — | — |
| Azimuth | https://github.com/MicrosoftResearch/Azimuth | — | Used as a dataset source only. |

### 9.2 Model weights — all require manual download

**No weights are in this repository, and none should be added.** Some are too large for
GitHub's 100 MB limit; AF3's licence prohibits redistribution outright. The `.gitignore`
already excludes `*.ckpt` and `*.tar`.

| Model | Weights file | Size | How to obtain | Blocker |
|---|---|---|---|---|
| **AlphaFold3** | `af3.bin.zst` → unpacked by `00_decompress_weights.pbs` | — | **Direct download**, no request form: https://storage.googleapis.com/alphafold3/af3.bin.zst — the filename `00_decompress_weights.pbs` already expects. | **Sharing prohibited** — see §9.2.1. |
| **Boltz-2** | `boltz2_conf.ckpt` | 2.29 GB | Downloaded by Boltz on first run, **from a login node only**. Then `scp` to scratch. | Exceeds GitHub's 100 MB limit. |
| **Boltz-2** | `mols.tar` (ligand cache) | ~1.7 GB | Unpacked by `00_install_boltz.pbs`; transfer manually with `scp`. | Same. |
| **TIGER** | Via **Git LFS submodule** | — | Install Git LFS **before** cloning, then `git clone --recursive`. | Silently absent if cloned wrongly. |
| **ESMFold** | ESM-2 checkpoint | ~2.6 GB | Auto-downloaded on first run. **Set `TORCH_HOME` to scratch first**, or it fills the home quota. | Quota, not licence. |
| **ProGen3** | `Profluent-Bio/progen3-3b` | — | Hugging Face; needs a token. | Requires an A100 to run at 3B. |

#### 9.2.1 AlphaFold3 weights — download is open, sharing is not

The parameters no longer require an approval request; they download directly from the URL
above. The licence terms are unchanged, and two clauses matter for this project:

| Clause | Effect here |
|---|---|
| Parameters "must not be published or shared" outside the organisation, and are treated as Google Confidential Information. Use is permitted only if they are "received directly from Google". | **Never commit `af3.bin` or `af3.bin.zst`, and do not pass them to anyone outside NTU.** Each person downloads their own copy. |
| Output may be published, shared and adapted, with notice of modification. | The structures and confidence scores in [`../results/alphafold3/`](../results/alphafold3/) are fine to publish. |
| Output **may not be used to train** machine learning models for biomolecular structure prediction similar to AF3. | Relevant to [`05_next_steps.md` §2.1](05_next_steps.md#21-add-oracle-scores-as-features-to-tiger). Feeding AF3 confidence scores into TIGER is predicting *guide activity*, not structure, so it reads as permitted — but confirm before publishing a model trained on AF3 output. |

Terms: https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md
(this is a summary, not legal advice).

Two cluster rules govern all of the above:

1. **Compute nodes have no outbound internet.** Every download happens on a login node, then
   moves to scratch. For the same reason Boltz's `--use_msa_server` works only from a login
   node.
2. **Large `scp` transfers to NSCC stall without the `-O` flag.**

### 9.3 Genetic databases (AlphaFold3 only)

| Asset | Size | Status in this project |
|---|---|---|
| AF3 genetic databases | **~600 GB** | **Skipped**, via `--norun_data_pipeline`, and a custom MSA supplied instead. Fetched by `alphafold3/fetch_databases.sh` upstream if needed. |

> **This shortcut caused the project's central failure.** Skipping the databases removed
> the only mechanism that would have built an MSA had the custom injection failed — which it
> did, silently. **If the data pipeline is skipped, verify the MSA reached the model:** check
> `chain_ptm` for the protein chain on the first complex before launching 500. Full account
> in [`04_results.md` §0](04_results.md#0-the-empty-msa-fault-read-before-1).

### 9.4 Datasets

| Dataset | Source | Notes |
|---|---|---|
| TIGER screens (primary) | TIGER repo, `.bz2` — unpack with `tiger/DECOMPRESSION.py` | Supplies the activity labels **and** the thermodynamic feature columns. |
| Konermann 2023 Cas13d orthologs | Paper supplementary files | 52 orthologs; the source for the curated MSA. |
| Azimuth V1 | Azimuth repo | Out-of-domain SpCas9 control. |
| Nucleaseq | Paper supplementary files | Acquired but unused; see [`05_next_steps.md` §3.1](05_next_steps.md#31-use-the-nucleaseq-dataset). |

Project working copies of the inputs are mirrored in a private Hugging Face dataset repo,
`yjjunnie/ureca-boltz-data`. Access must be requested, or a new repo created — see
[`../code/README.md` §4](../code/README.md#4-hugging-face-data-results-and-token-setup).

---

## 10. Python version matrix

Each model needs a different interpreter. These are not interchangeable; mixing them is the
single most common cause of lost time on this project.

| Model | Python | Key pins | Environment |
|---|---|---|---|
| AlphaFold3 | **3.12** | conda-provided `gcc` 12+ (system gcc 8.5.0 is too old) | conda, native install |
| Boltz-2 | **3.11** | `torch` matched to the node's CUDA; `nvidia-cublas-cu12>=12.5` | conda |
| ProGen3 | **3.10** | `torch==2.5.1+cu121`, prebuilt `flash_attn` wheel, `megablocks==0.7.0` | conda |
| TIGER | **3.9** | `tensorflow==2.11`, `pandas==1.5.2`, `biopython==1.80` | venv, local Windows |
| ESMFold | 3.10+ | `TORCH_HOME` redirected to scratch | conda |

Full dependency failure notes:
[`../code/README.md` §3a](../code/README.md#3a-dependencies--read-the-upstream-install-docs-first).
