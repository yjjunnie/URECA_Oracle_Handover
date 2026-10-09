# The job scripts

These are the scripts I wrote to run the models on NSCC. The models themselves aren't in
here — section 3 tells you how to get them.

If you've never used a computing cluster before, read section 1 first. If you have, skip to
section 2 and start replacing placeholders.

---

## 1. Cluster vocabulary

Quick definitions for the terms that show up everywhere below. If you already know these,
jump to section 2.

| Term | What it means |
|---|---|
| **NSCC ASPIRE** | The national supercomputer we have an allocation on. You log in to a *login node*, but your actual work runs on separate *compute nodes*. |
| **PBS** | The job scheduler. You don't run programs directly — you write a script, submit it to a queue, and PBS runs it on a compute node when resources free up. Could be seconds, could be hours. |
| **`qsub`** | The command that submits your script to the queue. `qstat` checks on it, `qdel` cancels it. |
| **walltime** | The maximum real-world time your job is allowed to run. Exceed it and PBS kills the job instantly, with no output. Always pad your estimate. |
| **scratch** | `/scratch/users/ntu/<YOUR_NSCC_ID>/` — big, fast storage for data and outputs. **It gets wiped periodically.** Your home directory is permanent but tiny. |
| **array job** | One script submitted as many numbered tasks (`#PBS -J 0-49`), so 500 complexes run as 50 parallel jobs instead of 500 separate submissions. |
| **module** | Software on the cluster isn't installed globally — you load it per job with `module load cuda/12.8.1`. Run `module avail` to see what exists. |
| **MSA** | Multiple sequence alignment: a stack of evolutionarily related protein sequences. Structure predictors use it to work out which parts of a protein contact each other. A protein with no MSA folds badly — this caused the biggest problem in the project, see the main README. |
| **pLDDT / pTM / ipTM** | Confidence scores from structure predictors. pLDDT runs 0–100 per residue (above ~70 is usable, ~30 means the model has no idea). pTM scores the whole structure 0–1; ipTM scores how well it got the *interface* between chains. |

The practical details — how to write the PBS header, which caches to redirect, how array
jobs work — are in [`../docs/02_nscc_job_scripts.md`](../docs/02_nscc_job_scripts.md).
Read that before submitting anything.

---

## 2. Replace the placeholders first

I stripped my own username and paths out of every script. Nothing here will run until you
put yours back in. There are two:

| Placeholder | Replace with | Example |
|---|---|---|
| `<YOUR_NSCC_ID>` | Your NSCC username | `/scratch/users/ntu/<YOUR_NSCC_ID>/logs` → `/scratch/users/ntu/abc123/logs` |
| `<PATH_TO_PROJECT>` | Where you keep the project locally | `<PATH_TO_PROJECT>/boltz` → `C:\Users\you\URECA_Code\boltz` |

Fastest way, once you're on NSCC:

```bash
cd code
grep -rl '<YOUR_NSCC_ID>' . | xargs sed -i 's|<YOUR_NSCC_ID>|abc123|g'
```

Check nothing was missed before you submit anything:

```bash
grep -rn '<YOUR_NSCC_ID>\|<PATH_TO_PROJECT>' .
```

If that prints nothing, you're ready.

**This isn't optional tidying.** Around 34 of those placeholders sit inside `#PBS -o` and
`#PBS -e` lines — the paths PBS writes your logs to. Submit without fixing them and the job
fails immediately.

While you're at it, create the log directory. PBS won't make it for you, and a job whose
log directory doesn't exist dies **silently, with no output whatsoever** — which is by far
the most confusing failure mode on this cluster:

```bash
mkdir -p /scratch/users/ntu/<YOUR_NSCC_ID>/logs
```

You'll also see `<dataset>`, `<jobid>` and `<index>` in some comments. Those aren't for you
to replace — they stand for values that change per run.

---

## 3. Getting the models

I deliberately didn't copy the models into this repo. Vendored copies go stale, bloat the
history, and make it unclear which lines are mine. Clone them fresh:

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

**Versions I actually used**, worth pinning — a newer upstream release may not match these
scripts:

- Boltz: `pip install boltz`, June 2025
- TIGER: the `NBT-submission` tag, if you want to reproduce the paper
- ProGen3: the 3B checkpoint, `Profluent-Bio/progen3-3b`

### Licences — one of these actually matters

If you're thinking of republishing any of this, the licences aren't all the same:

| Project | Licence | Can you redistribute it? |
|---|---|---|
| Boltz-2 | MIT | Yes, keep the licence + copyright |
| ProGen3 (code) | Apache 2.0 | Yes, keep the NOTICE/licence |
| ESM / ESMFold | MIT | Yes |
| Azimuth | BSD-style (Microsoft Research) | Yes, keep the notice |
| AlphaFold3 (code) | CC BY-NC-SA 4.0 | Non-commercial, attribution, **and ShareAlike** — republishing it can oblige you to license your own additions the same way |
| **TIGER** | **NYGC single-user, academic only** | **No** |

So TIGER is the real blocker, and AF3's ShareAlike clause is a trap you'd be opting into
for nothing. Pointing at upstream sidesteps both.

**Never commit model weights.** AF3's parameters prohibit redistribution outright, and
`boltz2_conf.ckpt` is 2.29 GB — GitHub rejects anything over 100 MB anyway. The
`.gitignore` already blocks `*.ckpt`, `*.tar` and friends.

---

## 4. Hugging Face: data, results, and your own token

Scratch gets wiped, so I used a **private Hugging Face dataset repo** as the real storage:

```
yjjunnie/ureca-boltz-data
├── data/              input datasets (TIGER, Konermann, Azimuth)
├── scripts/           copies of the pipeline scripts
├── results_fullprot/  the main Boltz analysis  → boltz/correlation_results/
└── results_balanced/  the balanced re-analysis → boltz/correlation_results/balanced/
```

You'll need your own access to it, or your own repo. Ask whoever supervises you to add you,
or just make a new one — `upload_to_hf.py` creates it if it doesn't exist.

### Setting up your token

A token is a password that lets scripts act on your HF account. You need one to upload, and
to download from a private repo.

1. Make an account at https://huggingface.co.
2. Click your avatar → **Settings** → **Access Tokens**.
3. **Create new token**. Pick **Write** if you'll upload results; **Read** is enough if
   you're only downloading.
4. Copy it immediately — HF only shows it once. It looks like `hf_AbCd1234...`.

### Using it without hardcoding it

**Never paste a token into a script.** Anything committed to git is permanent, even if you
delete it in a later commit. Set it as an environment variable instead — the scripts here
all read `os.environ["HF_TOKEN"]`.

**On NSCC / Linux:**

```bash
export HF_TOKEN="hf_your_token_here"
```

To make it stick between logins, put that line in `~/.bashrc` — your home directory, *not*
the repo.

PBS jobs don't inherit your shell environment by default, so you have to pass it in
explicitly when you submit:

```bash
qsub -v HF_TOKEN 06_upload_results.pbs
```

Alternatively, keep it in a file outside the repo and source it inside the job script:

```bash
source ~/.hf_token     # a file containing: export HF_TOKEN="hf_..."
```

**On Windows (PowerShell):**

```powershell
# Current session only
$env:HF_TOKEN = "hf_your_token_here"

# Permanent, for your user account
[Environment]::SetEnvironmentVariable("HF_TOKEN", "hf_your_token_here", "User")
```

### ⚠️ Revoke my old token

My token is still sitting in plaintext in the original working copy, in
`URECA_Code/boltz/download_results_from_hf.py` and `upload_to_hf.py`. It has write access
to the dataset repo. Please revoke it at https://huggingface.co/settings/tokens before that
folder goes anywhere.

### ⚠️ One bug I didn't fix

`download_results_from_hf.py` puts the balanced results in the wrong place. It writes them
to a sibling folder `correlation_results_balanced/`, but everything else in the project
expects them in `correlation_results/balanced/`. Run it as-is and you'll end up with two
directories and a lot of confusion. Fix the mapping before using it:

```python
DEST_DIRS = {
    "results_fullprot": os.path.join(BASE, "correlation_results"),
    "results_balanced": os.path.join(BASE, "correlation_results", "balanced"),
}
```

---

## 5. The scripts

### `boltz/` — start here

This is the cleanest pipeline I built, and the one to copy if you're adding a new model.
Run the numbered scripts in order.

| Script | What it does and why |
|---|---|
| `00_install_boltz.pbs` | Builds the Python environment and unpacks the ligand cache. CPU-only on purpose — installs take 30+ minutes and there's no reason to burn GPU time on them. Safe to re-run; it skips work already done. |
| `01_test_boltz.pbs` | Folds one tiny complex as a smoke test. **Don't skip this.** It prints the key names from the output JSON, which you need before you can write any parser. Guessing the key names and then re-running 1,300 GPU jobs is the mistake this avoids. |
| `02_fix_torch_cuda.pbs` | Only needed if `torch.cuda.is_available()` comes back `False`. Reinstalls PyTorch against the CUDA version the node actually has. |
| `generate_yamls.py` / `.pbs` | Builds one input YAML per guide, plus a `manifest.tsv` listing them all. Its last line prints the exact `#PBS -J` range to paste into the next script — use that instead of counting by hand. |
| `03_boltz_batch.pbs` | The actual inference. An array job, 20 guides per task. Each task copies its own inputs to a private folder first, so parallel tasks don't trip over each other. |
| `04_analyze.py` + `05_analyze.pbs` | Parses the confidence JSONs, correlates every metric against guide activity, writes the CSVs and plots. The `.py` does the work; the `.pbs` just runs it in a lightweight CPU environment. |
| `04b_analyze_balanced.py` + `05b_analyze_balanced.pbs` | Same analysis, but subsampled to 85 guides per Cas protein so the datasets are comparable. **This is the version to trust** — the unbalanced one confounds dataset with protein. |
| `06_upload_results.pbs` + `upload_to_hf.py` | Pushes results to Hugging Face. Run it as the last stage of every pipeline, not "later" — scratch gets wiped. |
| `download_from_hf.py` / `.pbs` | Pulls the input data and scripts *onto* NSCC. **Use the `.py` on a login node.** Compute nodes have no outbound internet, so the `.pbs` version will just fail to reach Hugging Face. |
| `download_results_from_hf.py` | Pulls finished results back *to Windows*. Note the bug in section 4. |
| `Boltz_Inference_Guide.ipynb` | My design notes from porting the AF3 setup to Boltz: the differences between the two input formats, how to reconstruct target sequences from spacers, the Azimuth `30mer` parsing rule, the direct-repeat sequences. **It has no saved outputs — it's notes, not results.** Read it before changing `generate_yamls.py`. |

### `alphafold3/` — read the warning first

**Before anything else: see the AF3 warning in the [main README](../README.md).** The
production run here folded CasRx with an empty MSA and the results are unreliable. The fix
exists but was only ever run on one complex.

Setup, in order:

| Script | What it does and why |
|---|---|
| `00_decompress_weights.pbs` | Unpacks the compressed AF3 weights into scratch. Once, before anything else. |
| `01_fill_casrx.pbs` + `fill_casrx_sequence.py` | Fetches the CasRx sequence from UniProt and substitutes it into the input JSONs, which ship with a placeholder. |
| `02_af3_msa.pbs` | Runs AF3's database search to build the MSA. CPU-only — this stage doesn't touch the neural network, so don't request a GPU for it. **This is the stage that silently failed.** |
| `reorganise_batches.py` | Shards 500 input JSONs into 50 folders of 10, so inference can run as a 50-task array job. |

Then pick an inference route:

| Script | When to use it |
|---|---|
| `03_af3_inference_batched.pbs` | The original. **This produced the broken run.** Only useful now as a reference for the array-job batching pattern. |
| `03b_af3_inference_custom_msa.pbs` | The custom-MSA fix, run through a Singularity container. **The container image it needs no longer exists on scratch**, so this won't run as-is — keep it as the worked container example. |
| **`03c_af3_inference_native.pbs`** + `install_af3_native.sh` | **Start here.** Same custom-MSA job as `03b` — same inputs, same outputs — but installed natively with conda instead of containerised. It also has a better preflight: it checks the weights exist, checks `import alphafold3` works, and prints `jax.devices()` before committing to a run. |

`03b` and `03c` do the same thing; the difference is only how AF3 is installed. Use `03c`
unless you've rebuilt the container image.

The three scripts that make `03b` work — this is the chain worth understanding:

| Script | What it does and why |
|---|---|
| `build_casrx_msa.py` | Builds the alignment from the 52 Cas13d orthologs in the Konermann dataset, instead of hoping AF3's database search finds homologs. Its docstring records the diagnosis of the pLDDT ≈ 30 problem. |
| `add_msa_to_json.py` | Injects the alignment *and* the protein sequence in a single pass. Both together on purpose: AF3 requires the first sequence of the alignment to exactly match the chain's `sequence` field, and doing it in one step stops them drifting apart. Supersedes `fill_casrx_sequence.py` for these inputs. |
| `fix_rna_pairedmsa.py` | Strips the `pairedMsa` key off RNA chains. It's a protein-only field; older AF3 builds ignored it, current ones throw `ValueError: Unexpected JSON keys`. |

Finally:

| Script | What it does |
|---|---|
| `04_analyze.pbs` + `analyze_af3_results.py` | Parses AF3 outputs, correlates confidence against activity, and runs partial correlations to test whether AF3 adds anything beyond the simple thermodynamic features. This is the version that actually produced the committed results — an unfinished refactor of it was removed, because it had a column-name mismatch that would crash before plotting. |

### `esmfold/`

| Script | What it does |
|---|---|
| `00_diagnose_plddt.py` + `.pbs` | **Unfinished — this is the easiest thing to pick up.** ESMFold was reporting ~30 average pLDDT on ordinary proteins, which can't be right. This folds reference proteins with known expected confidence (ubiquitin and GB1 should score 85–95; α-synuclein genuinely is disordered and should score 25–40) and prints four different ways of averaging pLDDT side by side. If ubiquitin scores ~90 the pipeline is fine and I was reading the wrong statistic; if it scores ~30 something is properly broken. Each protein is folded alone and in a batch, to catch padding contamination. |

### `progen3/`

Working, but I never pointed it at the Cas13 orthologs — that experiment is still open.

| File | What it's for |
|---|---|
| `NSCC_GUIDE.md` | A full standalone walkthrough: SSH in, set up, submit, monitor, fetch results. **The best starting point if you've never used NSCC** — it assumes nothing. |
| `nscc_setup.sh` | Builds the conda environment. Run once. |
| `nscc_score_job.sh` | Scores sequences from a FASTA file. Edit the config block near the top to point at your input. |
| `nscc_generate_job.sh` | Generates new sequences rather than scoring existing ones. |
| `SCORER_EXAMPLE.md` | Exact input/output shapes, so you know what you're getting. |
| `CODE_FLOW_GUIDE.md` | How the ProGen3 codebase fits together. |

GPU memory by model size: 112m ≈ 4 GB, 219m ≈ 8 GB, 339m ≈ 12 GB, 762m ≈ 20 GB, 1b ≈ 30 GB,
3b ≈ 40 GB (needs an A100). Use 3b if you can — but note the published accuracy curve is
flat beyond 3B, so there's nothing to gain from going larger.

### `tiger/`

TIGER is the benchmark everything else is measured against, and where the activity labels
come from. Runs on Windows.

| File | What it's for |
|---|---|
| `QUICK_START.md` | Read first. Gets you from nothing to a working install. |
| `INSTALLATION_GUIDE.md` | Full dependency list with pinned versions, plus troubleshooting. |
| `install_with_venv.bat` | Automated install into a virtual environment. |
| `test_installation.py` | Verifies every package imports and reports whether a GPU was found. |
| `CODE_FLOW_GUIDE.md` | How the TIGER codebase fits together. |
| `reimplementation_guide.md` | Notes from working through the model internals. |
| `COLUMN_EXPLANATIONS.md` | What every column in the prediction output means. |
| `DECOMPRESSION.py` | Unpacks the `.bz2` datasets. |
| `view_index_structure.py` | Inspects the multi-index on the prediction files. |

**TIGER needs Python 3.9 and TensorFlow 2.11 — it will not work on 3.11.** That trips
everyone up. And clone with `--recursive`, or the model weights silently won't be there.

---

## 6. Things that went wrong, and what they were

The errors I spent the most time on. [`../docs/02_nscc_job_scripts.md`](../docs/02_nscc_job_scripts.md)
has the longer list.

| Symptom | Cause |
|---|---|
| Job produces no output at all, not even an error | The log directory in your `#PBS -o` path doesn't exist. PBS won't create it and fails silently. `mkdir -p` it first. |
| `torch.cuda.is_available()` is `False` | Either you forgot `ngpus=1` in the resource line, or PyTorch was built for a different CUDA version. Run `02_fix_torch_cuda.pbs`. |
| Quota error during `pip install` | Caches defaulting to `/var/tmp` or home. Redirect `TMPDIR` and `PIP_CACHE_DIR` to scratch. |
| Quota error mid-inference | Same thing, but `TRITON_CACHE_DIR` this time. |
| Job dies with no error message | Walltime exceeded. |
| Array tasks mangle each other's files | They're sharing an input directory. Give each task its own. |
| Results vanished | Scratch was purged. Upload at the end of the pipeline, every time. |
| Large `scp` to NSCC stalls | Missing the `-O` flag. |
| `conda activate` fails inside a job | Use `source activate` in batch scripts. |
| AF3: `ValueError: Unexpected JSON keys in: pairedMsa` | RNA chain has a protein-only field. Run `fix_rna_pairedmsa.py`. |
| AF3: everything comes back pLDDT ≈ 30 | The protein MSA is empty. This is the big one — see the main README. |
