# Code — the pipeline scripts

**This is your own work, and it is the most valuable thing in the handover.**

None of the models are vendored here. What is here is the ~50 scripts written to *drive*
those models on NSCC: environment setup, input generation, batch submission, output
parsing, statistics, and result transfer. The models are a `pip install` or a `git clone`
away; this layer is not, and without it the next person re-derives weeks of cluster
debugging from scratch.

---

## 1. Why the model code is not here

Not primarily a licensing problem — mostly a maintenance one. Vendored copies of someone
else's repo go stale, bloat the history, and obscure which lines are yours. The standard
practice is: **depend on upstream at a pinned version, and version-control your own layer.**
That is what this directory does.

Licensing does matter for one of them, though. The five upstream licenses are not alike:

| Project | License | Redistribution |
|---|---|---|
| Boltz-2 | MIT | fine, keep the license + copyright |
| ProGen3 (code) | Apache 2.0 | fine, keep NOTICE/license |
| ESM / ESMFold | MIT | fine |
| Azimuth | BSD-style (Microsoft Research) | fine, keep the notice |
| AlphaFold3 (code) | **CC BY-NC-SA 4.0** | non-commercial only, attribution, *and* ShareAlike — redistributing it can oblige you to license your additions the same way |
| **TIGER** | **NYGC single-user, academic/non-commercial** | **do not redistribute** — it is a single-user license |

So: most of it *could* be republished, but TIGER should not be, and AF3's ShareAlike term
is a real constraint you would be opting into for no benefit. Referencing upstream avoids
the entire question.

**Model weights are a separate and stricter matter.** AF3 parameters require a request to
DeepMind under terms that prohibit redistribution. Never commit weights — see the
`.gitignore`.

---

## 2. Getting the upstream code

```bash
# Boltz-2 — just a pip install, no clone needed
pip install boltz

# AlphaFold3 (code; weights require a separate request to DeepMind)
git clone https://github.com/google-deepmind/alphafold3.git

# TIGER — --recursive matters: weights come via a Git LFS submodule
git clone --recursive https://github.com/daklab/tiger.git

# ProGen3
git clone https://github.com/profluent-ai/progen3.git

# ESM / ESMFold
git clone https://github.com/facebookresearch/esm.git

# Azimuth
git clone https://github.com/MicrosoftResearch/Azimuth.git
```

Versions this project actually used: Boltz via `pip install boltz` (June 2025), TIGER at
the `NBT-submission` tag for paper reproduction, ProGen3 3B checkpoint
(`Profluent-Bio/progen3-3b`). **Pin these** — a future upstream release may not match the
scripts here.

---

## 3. Layout

```
code/
├── boltz/        16 scripts + the inference-guide notebook — the most complete pipeline,
│                 and the best one to copy for a new model
├── alphafold3/   15 scripts — PBS stages, MSA construction, input generation, analysis
├── esmfold/      2 files  — the unresolved pLDDT diagnostic
├── progen3/      3 NSCC job scripts + 3 guides
└── tiger/        setup, docs and data helpers for running TIGER on Windows
```

Read `../docs/02_nscc_job_scripts.md` before running any of it, and
`../docs/01_oracles.md` for what each pipeline does and what it found.

### boltz/ — the reference pipeline

Numbered in execution order. If you only read one thing, read these:

| Script | Role |
|---|---|
| `00_install_boltz.pbs` | CPU job: venv + `pip install boltz` + extract `mols.tar`; idempotent |
| `01_test_boltz.pbs` | GPU smoke test — **prints the confidence-JSON keys**, which you need before writing any parser |
| `02_fix_torch_cuda.pbs` | remediation when `torch.cuda.is_available()` is False |
| `generate_yamls.py` / `.pbs` | build one YAML per guide + `manifest.tsv`; prints the array range to paste into the next script |
| `03_boltz_batch.pbs` | GPU array job, 20 guides per task |
| `04_analyze.py` + `05_analyze.pbs` | parse confidences, correlate, plot |
| `04b_analyze_balanced.py` + `05b_...pbs` | protein-balanced re-analysis |
| `upload_to_hf.py`, `download_*from_hf.py`, `05/06_upload_results.pbs` | push results off scratch before it is purged |
| `Boltz_Inference_Guide.ipynb` | design notes: AF3→Boltz differences, target reconstruction, the Azimuth `30mer` rule, DR sequences. **No executed outputs — it is a design document.** |

---

## 4. Before you run any of this

**Paths are hardcoded.** Every script contains `/scratch/users/ntu/hzhang08` and some
contain `c:\Users\holly\...`. Find and replace with your own:

```bash
grep -rl "hzhang08" . | xargs sed -i 's|/scratch/users/ntu/hzhang08|/scratch/users/ntu/YOUR_ID|g'
```

**The Hugging Face token has been removed.** The six scripts that touch HF originally had
a token hardcoded in plaintext. Here they read `os.environ["HF_TOKEN"]` instead:

```bash
export HF_TOKEN="hf_your_token_here"     # never commit this
python upload_to_hf.py
```

On NSCC, export it inside the job script from a file kept outside the repo.

⚠️ **The original token is still in plaintext in the working-tree copies** under
`URECA_Code/boltz/`. It grants write access to the private dataset
`yjjunnie/ureca-boltz-data` and should be revoked — see `../docs/05_next_steps.md` →
Known debts.

---

## 5. Provenance

Verified as own work by diffing against the upstream clones:

- **`tiger/`** — all 10 files are absent from the `daklab/tiger` clone (confirmed via
  `comm` against `tiger_full/` and `git status` inside it).
- **`boltz/`, `alphafold3/`, `esmfold/`** — written for this project; no upstream
  equivalent exists.
- **`progen3/nscc_*.sh`, `NSCC_GUIDE.md`** — reference NSCC, PBS and this account
  explicitly.

Judgment calls, flagged honestly: **`progen3/SCORER_EXAMPLE.md` and
`progen3/CODE_FLOW_GUIDE.md`** are not mentioned in the upstream README and match the
style of the other guides here, so they are very likely yours — but `progen3-main/` is not
a git clone, so this could not be verified by diff. Confirm before publishing, and drop
them if unsure. `progen3-main/setup.sh` *is* referenced in the upstream README and was
therefore left out.
