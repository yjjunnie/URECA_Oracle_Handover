# URECA Oracle Handover

Handover documentation for the URECA project on AI models for CRISPR-Cas13d guide RNA (gRNA)
design.

- **This file** — scope, results, status, repo layout, recommended next steps.
- **[`code/README.md`](code/README.md)** — how to run the pipelines.
- **[`docs/`](docs/)** — per-topic detail.

---

## 1. Objective

Selecting an effective gRNA for CRISPR-Cas13d knockdown is not possible by inspection of the
sequence alone. The current best predictor, **TIGER**, is a deep learning model trained
directly on large-scale screens in which thousands of guides were tested in cells, and so
requires expensive labelled data.

**Research question: can a pretrained model that has never seen knockdown data rank gRNAs?**

A positive result would allow guide design for a new Cas13 variant without first running a
screen. Three approaches were tested.

| Approach | Rationale | Models |
|---|---|---|
| Structure prediction | An effective guide should form a well-folded Cas13d:crRNA:target complex, so model *confidence* in the structure should track guide activity. | AlphaFold3, Boltz-2, ESMFold |
| Protein language model | Score the plausibility of a Cas13 protein sequence to screen new orthologs. | ProGen3 |
| RNA secondary structure | A guide can only bind if the target site is not already folded and inaccessible. | LinearFold / RNAfold |

---

## 2. Results

All figures are in [`docs/04_results.md`](docs/04_results.md).

**2.1 Structural confidence did not predict guide activity.** Approximately 1,800 complexes
were folded across two structure predictors and three Cas proteins. No confidence metric
(ipTM, pTM, pLDDT, ranking score) correlated meaningfully with measured guide activity.

Two constraints narrow this result:

1. The AlphaFold3 arm was invalid — see section 2.3.
2. Neither predictor was supplied an MSA. The result therefore applies to *MSA-free*
   structure prediction only. The 1,296 Boltz-2 complexes constitute the valid portion.

**2.2 Target-site accessibility outperformed all structural metrics.** The `log_unpaired`
feature (degree to which the target site is unfolded) reached ρ = −0.234, p = 1.2 × 10⁻⁷ —
several times stronger than any structure predictor metric. Structural scores added nothing
when tested as additional features on top of these simple features.

### 2.3 ⚠️ The AlphaFold3 arm is invalid

The 500-complex AF3 run was broken. The cause was identified too late in the project to
permit a re-run.

- **Symptom:** every complex returned mean pLDDT ≈ 30 and pTM ≈ 0.19. On AF3's confidence
  scale of roughly 0–100, pLDDT 30 indicates no usable prediction rather than a weak one.
- **Cause:** an empty protein MSA. An MSA (multiple sequence alignment) is a stack of
  evolutionarily related sequences that structure predictors use to infer intra-protein
  contacts. AF3's automatic database search returned no Cas13d homologs, so CasRx was folded
  without alignment information.
- **Fix:** written and validated, not applied at scale.
  `code/alphafold3/build_casrx_msa.py` builds a curated alignment from the 52 Cas13d
  orthologs in the Konermann dataset; `add_msa_to_json.py` injects it.

Effect of the curated MSA on a single TFRC-targeting complex:

| Metric | 500-run (AF3 automatic MSA) | Curated MSA |
|---|---|---|
| pTM | 0.19 | **0.85** |
| Protein chain pTM | 0.18 | **0.89** |
| Mean pLDDT | ~30 | **74.9** |

**Only one complex was run with the curated MSA.** Consequences for interpretation:

- The AF3 numbers in `docs/04_results.md` describe a pipeline that was not folding the
  protein. Treat that arm as provisional.
- The Boltz-2 arm is independent and unaffected.
- RNA chains remained poorly modelled even with the curated MSA (chain pTM 0.15 and 0.05),
  so the overall conclusion is unlikely to change — but this has not been tested and should
  not be written up as though it has.

---

## 3. Component status

| Component | State |
|---|---|
| **AlphaFold3** pipeline | ⚠️ 500 complexes run and analysed, but with a broken MSA (section 2.3). Fix written and validated on 1 complex; never re-run at scale. |
| **Boltz-2** pipeline | ✅ Complete — 4 datasets, plus a protein-balanced re-run. |
| **LinearFold / MFE baselines** | ✅ Complete — the strongest predictors found. |
| **TIGER** | ✅ Running locally; used as the source of activity labels. Never retrained. |
| **Azimuth** (SpCas9) | ✅ Used as an out-of-domain control. |
| **ESMFold** | ⚠️ Blocked — pLDDT values appeared incorrect; a diagnostic was written but never run to a conclusion. |
| **ProGen3** | ⚠️ Set up and working, but never pointed at the Cas13 orthologs. |

The two ⚠️ components are both near completion and are the recommended starting points.

---

## 4. Repository contents

| Path | Contents |
|---|---|
| [`code/`](code/) | Job scripts for running all pipelines on NSCC. Start here to run something. Model code is not vendored; `code/README.md` covers acquisition. |
| [`docs/01_oracles.md`](docs/01_oracles.md) | Per-model detail: function, expected performance, how it was run, outcome. |
| [`docs/02_nscc_job_scripts.md`](docs/02_nscc_job_scripts.md) | Writing and submitting NSCC jobs. Read before using the cluster. |
| [`docs/03_datasets.md`](docs/03_datasets.md) | Datasets, their columns, and the direction of "active" in each. |
| [`docs/04_results.md`](docs/04_results.md) | Complete results. |
| [`docs/05_next_steps.md`](docs/05_next_steps.md) | Ranked next steps with rationale. |
| [`docs/06_script_legend.md`](docs/06_script_legend.md) | **Legend of every script** — name, model, purpose, and which node it runs on — plus how to run one on NSCC and a full inventory of what must be downloaded manually (model code, weights, databases, datasets). |
| [`results/`](results/) | Output files, copied in so cluster access is not required to read them. |
| [`templates/`](templates/) | Blank PBS job scripts to copy. |

---

## 5. Getting started

1. **Request NSCC access.** Read [`docs/02_nscc_job_scripts.md`](docs/02_nscc_job_scripts.md)
   and arrange an account with GPU allocation. Accounts take longer to issue than expected;
   start this first.
2. **Verify the GPU environment before anything else.** Copy `templates/single_gpu.pbs`,
   substitute local paths, submit it, and confirm both `nvidia-smi` and
   `torch.cuda.is_available()` succeed. Environment and CUDA problems consumed the majority
   of project time, more than the research itself. A broken GPU setup is far cheaper to
   discover on day one than after a 6-hour batch job fails.
3. **Read the dependency notes before installing any model:**
   [`code/README.md` §3a](code/README.md#3a-dependencies--read-the-upstream-install-docs-first).
   Consult each upstream repository's own installation documentation first, as it is
   maintained and authoritative. §3a covers only the NSCC-specific failures: AlphaFold 3
   cannot use its container route without root, the login node's gcc is too old to compile
   it, `flash-attention` does not build so ProGen3 requires a version-pinned prebuilt wheel,
   and TIGER requires Python 3.9. None of this appears upstream, which assumes a
   conventional machine.
4. **Download the model weights.** None are in this repository. All download directly,
   including AlphaFold3's, but several are multi-gigabyte and must be fetched on a login
   node before transfer to scratch. Full inventory:
   [`docs/06_script_legend.md` §9](docs/06_script_legend.md#9-what-is-not-in-this-repository).
5. **Identify the relevant scripts** in
   [`docs/06_script_legend.md`](docs/06_script_legend.md), which lists every script with its
   model, purpose, run order, and whether it needs a GPU node, a CPU node, or a login node.
6. **Read [`docs/04_results.md`](docs/04_results.md)** to avoid re-running the experiment
   that already returned a null result, and to see which arm was invalid.
7. **Select a task** from [`docs/05_next_steps.md`](docs/05_next_steps.md).

---

## 6. Recommended next steps

In priority order. Full rationale, plus work to avoid repeating, is in
[`docs/05_next_steps.md`](docs/05_next_steps.md).

1. **Re-run the AF3 batch with the curated MSA.** The largest outstanding gap. The pipeline
   is built and validated on one complex (section 2.3) and needs only to be pointed at all
   500. Use `03c_af3_inference_native.pbs`, **not** `03_af3_inference_batched.pbs`, which
   produced the broken run. (`03b` runs the same fixed job via Singularity, but the
   container image is no longer on scratch, so `03c` is the working route.) The AF3 result
   is not usable until this is done.
2. **Complete the ESMFold diagnostic.** A few hours of work; the script is written and needs
   running and interpreting. This is a correctness question rather than a research one.
   Given the nature of the MSA problem, a similar confidence-averaging bug should be ruled
   out before any pLDDT value in this project is trusted.
3. **Run ProGen3 on the Konermann orthologs.** Entirely unrun, fully set up, and a
   self-contained result.
4. **Add oracle scores to TIGER as additional features** rather than testing them in
   isolation. Whether these metrics rank guides on their own is answered — they do not.
   Whether they add anything to a model that already works is the better question and was
   never addressed.

---

## 7. Immediate action required

A **Hugging Face access token is stored in plaintext** in the original working copy of the
project, in `URECA_Code/boltz/download_results_from_hf.py` and `upload_to_hf.py`. It has been
stripped from everything in this repository, but the originals still contain it.

**Revoke it** at https://huggingface.co/settings/tokens before sharing that folder or
publishing it. [`code/README.md`](code/README.md) covers correct token setup.
