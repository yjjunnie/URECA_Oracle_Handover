# The job scripts

Scripts for running the models on NSCC. Model code is not vendored here; section 3 covers
acquisition.

- No prior cluster experience: start at section 1.
- Otherwise: start at section 2 and replace the placeholders.

---

## 1. Cluster vocabulary

Definitions for terms used throughout this file.

| Term | Meaning |
|---|---|
| **NSCC ASPIRE** | The national supercomputer the project has an allocation on. Login happens on a *login node*; work runs on separate *compute nodes*. |
| **PBS** | The job scheduler. Programs are not run directly — a script is submitted to a queue, and PBS runs it on a compute node once resources free up. Delay ranges from seconds to hours. |
| **`qsub`** | Submits a script to the queue. `qstat` reports status; `qdel` cancels. |
| **walltime** | Maximum real-world runtime allowed. On exceeding it, PBS kills the job immediately with no output. Pad all estimates. |
| **scratch** | `/scratch/users/ntu/<YOUR_NSCC_ID>/` — large, fast storage for data and outputs. **Wiped periodically.** Home directories are permanent but small. |
| **array job** | One script submitted as many numbered tasks (`#PBS -J 0-49`), so 500 complexes run as 50 parallel jobs rather than 500 separate submissions. |
| **module** | Cluster software is not installed globally; it is loaded per job with e.g. `module load cuda/12.8.1`. `module avail` lists what exists. |
| **MSA** | Multiple sequence alignment: a stack of evolutionarily related protein sequences, used by structure predictors to infer intra-protein contacts. A protein with no MSA folds badly — the cause of the project's largest problem; see the main README. |
| **pLDDT / pTM / ipTM** | Structure predictor confidence scores. pLDDT is per-residue on a 0–100 scale (above ~70 is usable; ~30 indicates no usable prediction). pTM scores the whole structure 0–1; ipTM scores the *interface* between chains. |

Practical details — PBS header construction, cache redirection, array job mechanics — are in
[`../docs/02_nscc_job_scripts.md`](../docs/02_nscc_job_scripts.md). Read it before
submitting anything.

---

## 2. Replace the placeholders first

Usernames and absolute paths have been stripped from every script. Nothing will run until
they are restored. There are two placeholders:

| Placeholder | Replace with | Example |
|---|---|---|
| `<YOUR_NSCC_ID>` | NSCC username | `/scratch/users/ntu/<YOUR_NSCC_ID>/logs` → `/scratch/users/ntu/abc123/logs` |
| `<PATH_TO_PROJECT>` | Local project location | `<PATH_TO_PROJECT>/boltz` → `C:\Users\you\URECA_Code\boltz` |

Procedure, once on NSCC:

1. Substitute the NSCC ID:

   ```bash
   cd code
   grep -rl '<YOUR_NSCC_ID>' . | xargs sed -i 's|<YOUR_NSCC_ID>|abc123|g'
   ```

2. Confirm nothing was missed. This must print nothing before any submission:

   ```bash
   grep -rn '<YOUR_NSCC_ID>\|<PATH_TO_PROJECT>' .
   ```

3. Create the log directory. PBS does not create it, and a job whose log directory is
   missing dies **silently, with no output of any kind** — the most confusing failure mode
   on this cluster:

   ```bash
   mkdir -p /scratch/users/ntu/<YOUR_NSCC_ID>/logs
   ```

**This is not optional tidying.** Roughly 34 of the placeholders are inside `#PBS -o` and
`#PBS -e` lines, which define where PBS writes job logs. Submitting without fixing them
fails immediately.

`<dataset>`, `<jobid>` and `<index>` also appear in some comments. These are not for
substitution; they denote values that change per run.

---

## 3. Obtaining the models

Models were deliberately not copied into this repository: vendored copies go stale, bloat
history, and obscure which code is original to the project. Clone them fresh.

```bash
# Boltz-2 — no clone needed, it's on PyPI
pip install boltz

# AlphaFold3 — code only. Weights need a separate request to DeepMind.
git clone https://github.com/google-deepmind/alphafold3.git

# TIGER — --recursive matters, the weights come via a Git LFS submodule
git clone --recursive https://github.com/daklab/tiger.git

# ProGen3
git clone https://github.com/profluent-ai/progen3.git

# ESM / ESMFold
git clone https://github.com/facebookresearch/esm.git

# Azimuth
git clone https://github.com/MicrosoftResearch/Azimuth.git
```

**Versions used in this project**, worth pinning, as a newer upstream release may not match
these scripts:

- Boltz: `pip install boltz`, June 2025
- TIGER: the `NBT-submission` tag, to reproduce the paper
- ProGen3: the 3B checkpoint, `Profluent-Bio/progen3-3b`

### 3.1 Licences

Relevant to any republication of this work; the terms are not uniform.

| Project | Licence | Redistributable? |
|---|---|---|
| Boltz-2 | MIT | Yes, retain licence + copyright |
| ProGen3 (code) | Apache 2.0 | Yes, retain NOTICE/licence |
| ESM / ESMFold | MIT | Yes |
| Azimuth | BSD-style (Microsoft Research) | Yes, retain notice |
| AlphaFold3 (code) | CC BY-NC-SA 4.0 | Non-commercial, attribution, **and ShareAlike** — republication can oblige licensing original additions under the same terms |
| **TIGER** | **NYGC single-user, academic only** | **No** |

TIGER is therefore a hard blocker, and AF3's ShareAlike clause is an obligation incurred for
no benefit. Referencing upstream avoids both.

**Never commit model weights.** AF3's parameters prohibit redistribution outright, and
`boltz2_conf.ckpt` is 2.29 GB, above GitHub's 100 MB limit in any case. The `.gitignore`
already excludes `*.ckpt`, `*.tar` and similar.

---

## 3a. Dependencies — read the upstream install docs first

**Begin with each project's own README and installation docs on GitHub, every time.** Those
are maintained, updated when a dependency breaks, and authoritative. What follows is *not* a
substitute. It is the list of failures encountered **on NSCC specifically**, which upstream
docs will never cover because they assume root access and a conventional machine.

Dependencies consumed more project time than any scientific work. Budget accordingly. The
general shape of the problem: NSCC login nodes have an old toolchain, there is no root
access, and compute nodes have no outbound internet. Nearly every issue below reduces to one
of those three.

### 3a.1 AlphaFold 3 — the largest time sink

Read `alphafold3/docs/installation.md` upstream first, then `install_af3_native.sh` here,
whose header comments explain each workaround.

| Problem | Resolution |
|---|---|
| The official route requires `docker build` and a local Docker registry. **Both need root.** | Container abandoned. Installed natively with conda. |
| System `gcc` is **8.5.0** (2021), too old to compile `libcifpp`/`dssp`, which need C++17/20. | `conda install -c conda-forge gcc_linux-64 gxx_linux-64` provides gcc 12+ without root. Re-activate the environment afterwards so `CC`/`CXX` are exported, then assert `gcc >= 11`. |
| System `cmake` is 3.26.5; `pyproject.toml` requires **>= 3.28**. | Not an issue in practice — pip's build isolation fetches its own `cmake` + `ninja` wheels. Do not override it. |
| `pip install .` compiles C++ extensions — slow. | 10–30 minutes. **Run on a compute node**, not the login node, or CPU limits will kill it. No GPU required to build. |
| Half the AF3 Dockerfile builds HMMER from source. | Skipped. HMMER serves only the data pipeline (`jackhmmer`/`nhmmer` MSA search), and a custom MSA was supplied instead. |
| The genetic databases are **~600 GB**. | Skipped, via `--norun_data_pipeline`. |

Use Python 3.12 for this model. After install, run `build_data` to fetch the chemical
component database, then verify with `import alphafold3; jax.devices()`.

At runtime AF3 also requires the following, or it will crash or silently fall back to CPU:

```bash
export XLA_FLAGS='--xla_gpu_enable_triton_gemm=false'
export XLA_PYTHON_CLIENT_PREALLOCATE=true
export XLA_CLIENT_MEM_FRACTION=0.95
```

> ⚠️ **Relevance to the result.** Skipping the data pipeline and the 600 GB databases is
> *why* the protein MSA came back empty and the entire 500-complex run was wasted (see
> `../docs/04_results.md` §0). The shortcut was defensible, since a custom MSA was being
> supplied, but it removed the only mechanism that would have built one had the injection
> failed. **If the data pipeline is skipped, verify that the MSA actually reached the
> model.** Check `chain_ptm` for the protein chain on the first complex before launching
> 500.

### 3a.2 ProGen3 — the prebuilt wheel

**`flash-attention` does not reliably compile on NSCC.** Building from source is a long
C++/CUDA build that failed repeatedly, so a prebuilt wheel pinned to the exact
Python/torch/CUDA combination is installed instead. The 187 MB `flash_attn.whl` in
`progen3-main/` is a cached copy of:

```bash
pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.5cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
```

That filename is a contract: `cu12`, `torch2.5`, `cxx11abiFALSE`, `cp310` (Python 3.10).
**Changing the Python or torch version invalidates this wheel**, and the matching one must
be taken from the
[flash-attention releases page](https://github.com/Dao-AILab/flash-attention/releases).
This is why the environment is pinned to Python 3.10 and `torch==2.5.1+cu121`.

Two further constraints in `nscc_setup.sh`:

- `megablocks==0.7.0` requires `--no-build-isolation`, and is installed without the `[gg]`
  extra to avoid pulling in grouped-GEMM build dependencies.
- `grouped_gemm` installs from git and **requires a GPU present at install time**, so the
  setup must run as a GPU job rather than on the login node.

One correction was made to that script during handover: the first verification line called
`torch.cuda.is_available__()` (two underscores), which would raise `AttributeError` instead
of reporting CUDA status. That is the explanation for any such error seen previously.

### 3a.3 Boltz-2 — straightforward apart from torch/CUDA

`pip install boltz` on Python 3.11 is nearly sufficient. The one recurring failure is torch
built against a different CUDA version than the node provides. `01_test_boltz.pbs` detects
it; `02_fix_torch_cuda.pbs` corrects it. Set `CUDA_TAG` to match `nvidia-smi` output
(`cu118`, `cu121`, `cu124`).

Two non-obvious pins in that fix script, both established by trial and error:

- `cuequivariance-torch` and `cuequivariance-ops-torch-cu12` install with `--no-deps`;
  otherwise pip pulls in CUDA toolkit 13 and breaks the rest of the environment.
- `nvidia-cublas-cu12>=12.5` — `cuequivariance` calls `cublasGemmGroupedBatchedEx`, which
  exists only from cuBLAS 12.5. Upgrading cuBLAS alone remains within the CUDA 12 family.

Weights (`boltz2_conf.ckpt`, `mols.tar`) must be transferred in manually via `scp`, as
compute nodes cannot download them. For the same reason, `--use_msa_server` works only from
a login node.

### 3a.4 TIGER — the Python version trap

**TIGER requires Python 3.9 and TensorFlow 2.11.** Not 3.11, and not a newer TensorFlow.
Resolving this consumed an afternoon before an old Python was installed alongside the main
one; `tiger/QUICK_START.md` contains the walkthrough and `install_with_venv.bat` automates
it on Windows. `requirements.txt` is fully pinned (`pandas==1.5.2`, `biopython==1.80`,
`shap==0.42.1`, …) — do not unpin it to satisfy another package.

Model weights arrive through a **Git LFS submodule**. Install Git LFS *before* cloning and
use `git clone --recursive`. Cloning incorrectly leaves the weights silently absent,
producing a working install that cannot predict anything.

### 3a.5 ESMFold

Set `TORCH_HOME` to scratch before the first run, or the ~2.6 GB checkpoint lands in the
home directory and exhausts the quota. See `esmfold/00_diagnose_plddt.pbs`.

### 3a.6 Unlisted problems

Escalation order:

1. The upstream repository's `installation.md` or README.
2. Its GitHub **Issues**, including closed ones — most CUDA/compiler combinations have
   already been encountered by someone.
3. `module avail` on NSCC, to see which toolchains currently exist, as the ones used here
   may have moved.

Record whatever is established. That is the sole origin of this section.

---

## 4. Hugging Face: data, results, and token setup

Scratch is wiped periodically, so a **private Hugging Face dataset repo** served as the
authoritative storage:

```
yjjunnie/ureca-boltz-data
├── data/              input datasets (TIGER, Konermann, Azimuth)
├── scripts/           copies of the pipeline scripts
├── results_fullprot/  the main Boltz analysis  → boltz/correlation_results/
└── results_balanced/  the balanced re-analysis → boltz/correlation_results/balanced/
```

Access to this repo must be requested from the project supervisor, or a new repo created —
`upload_to_hf.py` creates one if it does not exist.

### 4.1 Creating a token

A token is a credential allowing scripts to act on a Hugging Face account. One is required
to upload, and to download from a private repo.

1. Create an account at https://huggingface.co.
2. Avatar → **Settings** → **Access Tokens**.
3. **Create new token.** Select **Write** for uploading results; **Read** suffices for
   downloading only.
4. Copy it immediately — Hugging Face displays it once. Format: `hf_AbCd1234...`.

### 4.2 Using a token without hardcoding it

**Never paste a token into a script.** Anything committed to git is permanent, even if
removed in a later commit. Use an environment variable instead; all scripts here read
`os.environ["HF_TOKEN"]`.

NSCC / Linux:

```bash
export HF_TOKEN="hf_your_token_here"
```

To persist it between logins, add that line to `~/.bashrc` — in the home directory, *not*
the repo.

PBS jobs do not inherit the shell environment by default, so the variable must be passed
explicitly at submission:

```bash
qsub -v HF_TOKEN 06_upload_results.pbs
```

Alternatively, keep it in a file outside the repo and source it inside the job script:

```bash
source ~/.hf_token     # a file containing: export HF_TOKEN="hf_..."
```

Windows (PowerShell):

```powershell
# Current session only
$env:HF_TOKEN = "hf_your_token_here"

# Permanent, for the current user account
[Environment]::SetEnvironmentVariable("HF_TOKEN", "hf_your_token_here", "User")
```

### 4.3 ⚠️ Revoke the previous token

The previous token remains in plaintext in the original working copy, in
`URECA_Code/boltz/download_results_from_hf.py` and `upload_to_hf.py`. It has write access to
the dataset repo. Revoke it at https://huggingface.co/settings/tokens before that folder is
distributed.

### 4.4 ⚠️ Known unfixed bug

`download_results_from_hf.py` writes the balanced results to the wrong location: a sibling
folder `correlation_results_balanced/`, whereas the rest of the project expects
`correlation_results/balanced/`. Running it unmodified produces two directories and
considerable confusion. Correct the mapping before use:

```python
DEST_DIRS = {
    "results_fullprot": os.path.join(BASE, "correlation_results"),
    "results_balanced": os.path.join(BASE, "correlation_results", "balanced"),
}
```

---

## 5. The scripts

### 5.1 `boltz/` — start here

The cleanest pipeline in the project, and the one to copy when adding a new model. Run the
numbered scripts in order.

| Script | Function and rationale |
|---|---|
| `00_install_boltz.pbs` | Builds the Python environment and unpacks the ligand cache. CPU-only by design — installation takes 30+ minutes and does not warrant GPU time. Safe to re-run; it skips completed work. |
| `01_test_boltz.pbs` | Folds one small complex as a smoke test. **Do not skip.** It prints the key names from the output JSON, which are prerequisites for writing any parser. Guessing key names and then re-running 1,300 GPU jobs is the error this avoids. |
| `02_fix_torch_cuda.pbs` | Required only if `torch.cuda.is_available()` returns `False`. Reinstalls PyTorch against the CUDA version actually present on the node. |
| `generate_yamls.py` / `.pbs` | Builds one input YAML per guide, plus a `manifest.tsv` listing all of them. Its final line prints the exact `#PBS -J` range for the next script; use that rather than counting manually. |
| `03_boltz_batch.pbs` | The inference stage. An array job, 20 guides per task. Each task copies its inputs to a private folder first, so parallel tasks do not collide. |
| `04_analyze.py` + `05_analyze.pbs` | Parses the confidence JSONs, correlates every metric against guide activity, and writes the CSVs and plots. The `.py` performs the work; the `.pbs` runs it in a lightweight CPU environment. |
| `04b_analyze_balanced.py` + `05b_analyze_balanced.pbs` | The same analysis, subsampled to 85 guides per Cas protein so datasets are comparable. **This is the authoritative version** — the unbalanced analysis confounds dataset with protein. |
| `06_upload_results.pbs` + `upload_to_hf.py` | Pushes results to Hugging Face. Run as the final stage of every pipeline, not deferred — scratch is wiped. |
| `download_from_hf.py` / `.pbs` | Pulls input data and scripts *onto* NSCC. **Use the `.py` on a login node.** Compute nodes have no outbound internet, so the `.pbs` variant cannot reach Hugging Face. |
| `download_results_from_hf.py` | Pulls finished results back to Windows. Subject to the bug in section 4.4. |
| `Boltz_Inference_Guide.ipynb` | Design notes from porting the AF3 setup to Boltz: differences between the two input formats, reconstruction of target sequences from spacers, the Azimuth `30mer` parsing rule, and the direct-repeat sequences. **Contains no saved outputs — notes, not results.** Read before modifying `generate_yamls.py`. |

### 5.2 `alphafold3/` — read the warning first

**Prerequisite: the AF3 warning in the [main README](../README.md).** The production run
here folded CasRx with an empty MSA, and its results are unreliable. The fix exists but was
only ever run on one complex.

Setup, in order:

| Script | Function and rationale |
|---|---|
| `00_decompress_weights.pbs` | Unpacks the compressed AF3 weights into scratch. Run once, before anything else. |
| `01_fill_casrx.pbs` + `fill_casrx_sequence.py` | Fetches the CasRx sequence from UniProt and substitutes it into the input JSONs, which ship with a placeholder. |
| `02_af3_msa.pbs` | Runs AF3's database search to build the MSA. CPU-only — this stage does not touch the neural network, so no GPU should be requested. **This is the stage that silently failed.** |
| `reorganise_batches.py` | Shards 500 input JSONs into 50 folders of 10, so inference can run as a 50-task array job. |

Then select an inference route:

| Script | When to use |
|---|---|
| `03_af3_inference_batched.pbs` | The original. **This produced the broken run.** Retained only as a reference for the array-job batching pattern. |
| `03b_af3_inference_custom_msa.pbs` | The custom-MSA fix, run through a Singularity container. **The required container image no longer exists on scratch**, so this will not run as-is. Retained as a worked container example. |
| **`03c_af3_inference_native.pbs`** + `install_af3_native.sh` | **Start here.** The same custom-MSA job as `03b` — same inputs, same outputs — but installed natively with conda rather than containerised. It also has a better preflight: it verifies the weights exist, verifies `import alphafold3` works, and prints `jax.devices()` before committing to a run. |

`03b` and `03c` are functionally identical; they differ only in how AF3 is installed. Use
`03c` unless the container image has been rebuilt.

The three scripts that make `03b` work, and the chain worth understanding:

| Script | Function and rationale |
|---|---|
| `build_casrx_msa.py` | Builds the alignment from the 52 Cas13d orthologs in the Konermann dataset, rather than relying on AF3's database search to find homologs. Its docstring records the diagnosis of the pLDDT ≈ 30 problem. |
| `add_msa_to_json.py` | Injects the alignment *and* the protein sequence in a single pass. Both together by design: AF3 requires the first sequence of the alignment to match the chain's `sequence` field exactly, and a single step prevents the two drifting apart. Supersedes `fill_casrx_sequence.py` for these inputs. |
| `fix_rna_pairedmsa.py` | Strips the `pairedMsa` key from RNA chains. It is a protein-only field; older AF3 builds ignored it, current ones raise `ValueError: Unexpected JSON keys`. |

Analysis:

| Script | Function |
|---|---|
| `04_analyze.pbs` + `analyze_af3_results.py` | Parses AF3 outputs, correlates confidence against activity, and runs partial correlations to test whether AF3 adds anything beyond the simple thermodynamic features. This is the version that produced the committed results; an unfinished refactor was removed, as it had a column-name mismatch that would crash before plotting. |

### 5.3 `esmfold/`

| Script | Function |
|---|---|
| `00_diagnose_plddt.py` + `.pbs` | **Unfinished — the easiest component to pick up.** ESMFold was reporting ~30 average pLDDT on ordinary proteins, which cannot be correct. This folds reference proteins of known expected confidence (ubiquitin and GB1 should score 85–95; α-synuclein is genuinely disordered and should score 25–40) and prints four methods of averaging pLDDT side by side. A ubiquitin score near 90 indicates the pipeline is sound and the wrong statistic was being read; a score near 30 indicates a genuine defect. Each protein is folded both alone and in a batch, to detect padding contamination. |

### 5.4 `progen3/`

Working, but never pointed at the Cas13 orthologs; that experiment remains open.

| File | Purpose |
|---|---|
| `NSCC_GUIDE.md` | A standalone walkthrough: SSH access, setup, submission, monitoring, result retrieval. **The best starting point for anyone new to NSCC** — it assumes no prior knowledge. |
| `nscc_setup.sh` | Builds the conda environment. Run once. |
| `nscc_score_job.sh` | Scores sequences from a FASTA file. Edit the config block near the top to specify the input. |
| `nscc_generate_job.sh` | Generates new sequences rather than scoring existing ones. |
| `SCORER_EXAMPLE.md` | Exact input/output shapes. |
| `CODE_FLOW_GUIDE.md` | Structure of the ProGen3 codebase. |

GPU memory by model size: 112m ≈ 4 GB, 219m ≈ 8 GB, 339m ≈ 12 GB, 762m ≈ 20 GB, 1b ≈ 30 GB,
3b ≈ 40 GB (requires an A100). Prefer 3b where available; note that the published accuracy
curve is flat beyond 3B, so larger models offer no gain.

### 5.5 `tiger/`

TIGER is the benchmark against which everything else is measured, and the source of the
activity labels. Runs on Windows.

| File | Purpose |
|---|---|
| `QUICK_START.md` | Read first. Covers installation from nothing to working. |
| `INSTALLATION_GUIDE.md` | Full dependency list with pinned versions, plus troubleshooting. |
| `install_with_venv.bat` | Automated install into a virtual environment. |
| `test_installation.py` | Verifies every package imports and reports GPU detection. |
| `CODE_FLOW_GUIDE.md` | Structure of the TIGER codebase. |
| `reimplementation_guide.md` | Notes on the model internals. |
| `COLUMN_EXPLANATIONS.md` | Definition of every column in the prediction output. |
| `DECOMPRESSION.py` | Unpacks the `.bz2` datasets. |
| `view_index_structure.py` | Inspects the multi-index on the prediction files. |

**TIGER requires Python 3.9 and TensorFlow 2.11; it will not work on 3.11.** Clone with
`--recursive`, or the model weights will silently be absent.

---

## 6. Troubleshooting

The errors that consumed the most time.
[`../docs/02_nscc_job_scripts.md`](../docs/02_nscc_job_scripts.md) has the longer list.

| Symptom | Cause |
|---|---|
| Job produces no output at all, not even an error | The log directory in the `#PBS -o` path does not exist. PBS will not create it and fails silently. Create it with `mkdir -p` first. |
| `torch.cuda.is_available()` returns `False` | Either `ngpus=1` is missing from the resource line, or PyTorch was built for a different CUDA version. Run `02_fix_torch_cuda.pbs`. |
| Quota error during `pip install` | Caches defaulting to `/var/tmp` or home. Redirect `TMPDIR` and `PIP_CACHE_DIR` to scratch. |
| Quota error mid-inference | The same cause, via `TRITON_CACHE_DIR`. |
| Job dies with no error message | Walltime exceeded. |
| Array tasks corrupt each other's files | They are sharing an input directory. Give each task its own. |
| Results missing | Scratch was purged. Upload at the end of the pipeline, every time. |
| Large `scp` to NSCC stalls | The `-O` flag is missing. |
| `conda activate` fails inside a job | Use `source activate` in batch scripts. |
| AF3: `ValueError: Unexpected JSON keys in: pairedMsa` | An RNA chain carries a protein-only field. Run `fix_rna_pairedmsa.py`. |
| AF3: all complexes return pLDDT ≈ 30 | The protein MSA is empty. See the main README; this is the project's central failure. |
