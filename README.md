# URECA Oracle Handover

Handover documentation for the AI4CRISPR / URECA project: an evaluation of whether
pretrained biological "oracle" models can predict **CRISPR-Cas13d guide RNA activity**.

Everything here is written for someone picking the project up cold. Read this file,
then `docs/` in order.

---

## 1. The question the project was asking

Cas13d guide (gRNA) design currently relies on supervised models trained directly on
screen data — **TIGER** being the strongest. Those models need large labelled screens.

The project asked whether a general-purpose pretrained model could substitute for that
labelled data — i.e. whether a model that was never trained on knockdown activity could
still rank guides. Three families were considered:

| Family | Idea being tested | Models tried |
|---|---|---|
| Structure prediction | A good guide forms a better-folded Cas13d:crRNA:target complex, so **structural confidence should track activity** | AlphaFold3, Boltz-2, ESMFold |
| Protein language model | Sequence likelihood as a proxy for whether a Cas13 ortholog is plausible/functional | ProGen3 |
| RNA secondary structure | Target-site accessibility drives activity | LinearFold / RNAfold (MFE, unpaired probability) |

**Headline result: the structural-confidence hypothesis did not hold.** See
`docs/04_results.md`. Confidence metrics (ipTM, pTM, pLDDT, ranking score) show
essentially no correlation with measured guide activity, while trivial RNA-structure
baselines beat all of them. This is a clean, useful negative result — it is the main
scientific output so far.

---

## 2. Status at handover

| Component | State | Where |
|---|---|---|
| AlphaFold3 pipeline on NSCC | **Complete**, 500 complexes run + analysed | `alphafold3/my_parts/` |
| Boltz-2 pipeline on NSCC | **Complete**, run on 4 datasets + a protein-balanced re-run | `boltz/` |
| ESMFold | **Blocked / unresolved** — pLDDT diagnostic written but never concluded | `esmfold_test/` |
| ProGen3 | **Set up, not applied** — scorer runs, never used on Cas13 orthologs | `progen3-main/` |
| TIGER | **Reproduced locally + used as data source**, not retrained | `tiger-main/` |
| Azimuth (SpCas9) | Used only as an out-of-domain comparison dataset | `Azimuth-master/` |
| LinearFold / MFE baselines | Computed, and they are the best predictors found | inside AF3 analysis |

See `docs/05_next_steps.md` for what is worth doing next.

---

## 3. Repository map (the parent `URECA_Code` folder)

```
URECA_Code/
├── alphafold3/            # DeepMind AF3 source
│   └── my_parts/          # ★ all project-written AF3 work (PBS, input gen, analysis)
├── boltz/                 # ★ complete Boltz-2 pipeline (project-written)
├── boltz-main/            # Boltz upstream source
├── boltz2_conf.ckpt       # Boltz-2 weights, 2.29 GB  (NOT in git)
├── mols.tar               # Boltz CCD ligand cache, 1.86 GB  (NOT in git)
├── esmfold_test/          # ★ ESMFold pLDDT diagnostic
├── esm/                   # ESM/ESMFold source
├── progen3-main/          # ProGen3 + project-written NSCC job scripts
├── tiger-main/            # TIGER, two copies (see docs/03_datasets.md)
├── Azimuth-master/        # SpCas9 on-target model (Doench)
├── [Konermann 2023] *.csv/.xlsx   # Cas13d ortholog + screen data
├── [Nucleaseq] Supplemental_File_1.xlsx
└── 26May_AI4CRISPR_slides .pdf    # project presentation (annex slides)
```

★ = written for this project. Everything else is upstream code or data.

**Note:** the large weight files (`boltz2_conf.ckpt`, `mols.tar`) and the `.ckpt`/`.tar`
artifacts are deliberately excluded from version control. `docs/01_oracles.md` records
where to re-obtain each one.

---

## 4. Documentation index

| Doc | Contents |
|---|---|
| [`docs/01_oracles.md`](docs/01_oracles.md) | Every oracle model: what it does, published performance, how it was run here, what came of it |
| [`docs/02_nscc_job_scripts.md`](docs/02_nscc_job_scripts.md) | **How to write and submit your own PBS job scripts on NSCC ASPIRE** — the practical core of this handover |
| [`docs/03_datasets.md`](docs/03_datasets.md) | TIGER, Konermann, Azimuth, Nucleaseq datasets: contents, columns, activity conventions |
| [`docs/04_results.md`](docs/04_results.md) | All quantitative findings, with the numbers |
| [`docs/05_next_steps.md`](docs/05_next_steps.md) | Open threads, ranked by value |
| [`results/`](results/) | The actual analysis outputs, copied in so this repo stands alone |
| [`templates/`](templates/) | Copy-paste PBS templates (single GPU job, array job, CPU analysis job) |

---

## 5. Minimum viable restart

If you want to be productive within a day:

1. Read `docs/02_nscc_job_scripts.md` and get an NSCC account with GPU allocation.
2. Copy `templates/single_gpu.pbs`, change the paths to your own scratch, submit it,
   confirm `nvidia-smi` and `torch.cuda.is_available()` both work. **Do this before
   anything else** — most time lost on this project went to environment issues, not science.
3. Read `docs/04_results.md` so you do not re-run the structural-confidence experiment
   that has already returned a null result.
4. Pick a thread from `docs/05_next_steps.md`.
