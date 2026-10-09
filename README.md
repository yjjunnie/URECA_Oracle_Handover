# URECA Oracle Handover

This is everything I built and found during my URECA project on AI models for CRISPR-Cas13d
guide RNA design. I'm writing it for whoever picks this up next.

I've assumed you're new to the project and possibly new to research computing generally.
Where I use a term you might not have met yet, I explain it. Read this file first, then
`code/README.md` if you want to start running things, or `docs/` if you want the full story.

---

## 1. The question I was trying to answer

When you use CRISPR-Cas13d to knock down a gene, you have to pick a **guide RNA** (gRNA) —
a short sequence that tells the enzyme where to cut. Some guides work brilliantly, some do
nothing, and you can't tell which just by looking at them.

The best current predictor is **TIGER**, a deep learning model trained directly on large
screens where thousands of guides were tested in cells. That works, but it needs that
expensive labelled data in the first place.

**My question: could a pretrained model that has never seen knockdown data still rank guides?**

If yes, you could design guides for any new Cas13 variant without running a screen first.
I tested three ideas:

| Idea | The reasoning | Models I tried |
|---|---|---|
| Structure prediction | A guide that really engages its target should form a well-folded Cas13d:crRNA:target complex. So the model's *confidence* in the structure should track how well the guide works. | AlphaFold3, Boltz-2, ESMFold |
| Protein language model | Score how "plausible" a Cas13 protein sequence is, to screen new orthologs | ProGen3 |
| RNA secondary structure | A guide can only bind if its target site isn't already folded up and inaccessible | LinearFold / RNAfold |

---

## 2. What I found

**The structural confidence idea didn't work — for the version of it I actually managed to
test.** I folded about 1,800 complexes in total across two structure predictors and three
Cas proteins. No confidence metric — ipTM, pTM, pLDDT, ranking score — correlated
meaningfully with measured guide activity.

Two caveats I want you to carry forward, because they narrow this a lot. The AlphaFold3
half turned out to be broken (see the box below). And **neither** predictor was given an
MSA, so what I really showed is that *MSA-free* structure prediction doesn't predict guide
activity. That leaves 1,296 Boltz-2 complexes as the solid part of the result.

What *did* work was far simpler. **Target-site accessibility** (`log_unpaired`, basically
"how unfolded is the target site") reached ρ = −0.234, p = 1.2 × 10⁻⁷ — several times
stronger than anything the structure predictors produced. I also checked whether the
structural scores added anything *on top of* those simple features. They added nothing.

All numbers are in [`docs/04_results.md`](docs/04_results.md).

### ⚠️ Read this before you trust the AlphaFold3 half of that result

**The 500-complex AF3 run was broken, and I found out why too late to redo it.**

Every one of those complexes came back with mean pLDDT around 30 and pTM around 0.19.
pLDDT is AF3's confidence score, roughly 0–100; 30 means "I have no idea". That's not a
weak prediction, that's no prediction at all.

The cause was an **empty protein MSA**. An MSA (multiple sequence alignment) is a stack of
evolutionarily related sequences that structure predictors rely on to infer which parts of
a protein touch each other. AF3's automatic database search didn't find Cas13d homologs,
so it folded CasRx with nothing to go on.

I wrote the fix: `code/alphafold3/build_casrx_msa.py` builds a curated alignment from the
52 Cas13d orthologs in the Konermann dataset, and `add_msa_to_json.py` injects it. On a
TFRC-targeting complex, the difference is not subtle:

| | 500-run (AF3's own MSA) | with my curated MSA |
|---|---|---|
| pTM | 0.19 | **0.85** |
| protein chain pTM | 0.18 | **0.89** |
| mean pLDDT | ~30 | **74.9** |

**I only ever ran one complex this way.** The fix is validated, not applied.

So: the AF3 numbers in `docs/04_results.md` test a pipeline that wasn't folding the
protein. Treat that half of the result as provisional. The Boltz-2 half is independent and
still stands on its own, and the RNA chains stayed poorly modelled even with the good MSA
(chain pTM 0.15 and 0.05), so I don't expect the conclusion to flip — but it hasn't
actually been tested yet, and you shouldn't write it up as though it has.

---

## 3. Where I left things

| Component | State |
|---|---|
| **AlphaFold3** pipeline | ⚠️ 500 complexes run and analysed, **but with a broken MSA** — see the warning in section 2. Fix written and validated on 1 complex, never re-run at scale. |
| **Boltz-2** pipeline | ✅ Done — 4 datasets, plus a protein-balanced re-run |
| **LinearFold / MFE baselines** | ✅ Done — and they turned out to be the best predictors |
| **TIGER** | ✅ Running locally; used as my source of activity labels. Never retrained. |
| **Azimuth** (SpCas9) | ✅ Used as an out-of-domain control |
| **ESMFold** | ⚠️ Blocked — pLDDT looked wrong, I wrote a diagnostic, never ran it to a conclusion |
| **ProGen3** | ⚠️ Set up and working, but I never actually pointed it at the Cas13 orthologs |

The two ⚠️ rows are the obvious places to start. Both are close to done.

---

## 4. What's in this repo

| Folder | What it's for |
|---|---|
| [`code/`](code/) | The job scripts I wrote to run all of this on NSCC. **Start here if you want to run something.** The models themselves aren't included — that README explains how to get them. |
| [`docs/01_oracles.md`](docs/01_oracles.md) | Each model: what it does, how well it's supposed to work, how I ran it, what came of it |
| [`docs/02_nscc_job_scripts.md`](docs/02_nscc_job_scripts.md) | How to write and submit jobs on NSCC. Read before you touch the cluster. |
| [`docs/03_datasets.md`](docs/03_datasets.md) | The datasets, their columns, and which direction "active" means in each one |
| [`docs/04_results.md`](docs/04_results.md) | Every number I got |
| [`docs/05_next_steps.md`](docs/05_next_steps.md) | What I'd do next, ranked |
| [`results/`](results/) | The actual output files, copied in so you don't need cluster access to read them |
| [`templates/`](templates/) | Blank PBS job scripts to copy when writing your own |

---

## 5. If you only have one day

1. Read [`docs/02_nscc_job_scripts.md`](docs/02_nscc_job_scripts.md) and get an NSCC account
   with GPU allocation sorted. The account takes longer to arrive than you'd expect, so
   start it immediately.
2. Copy `templates/single_gpu.pbs`, put your own paths in, submit it, and confirm that
   `nvidia-smi` and `torch.cuda.is_available()` both come back working.

   **Do this before anything else.** Most of the time I lost on this project went to
   environment and CUDA problems, not to the actual science. Finding out your GPU setup is
   broken on day one is much better than finding out after a 6-hour batch job fails.
3. Read [`docs/04_results.md`](docs/04_results.md) so you don't accidentally re-run the
   experiment that already came back null.
4. Pick something from [`docs/05_next_steps.md`](docs/05_next_steps.md).

---

## 6. What I'd pick up first

If it were me, in this order:

1. **Re-run the AF3 batch with the curated MSA.** This is the biggest hole I left. The
   pipeline is built and validated on one complex (see the warning in section 2) — it just
   needs pointing at all 500. Use `03c_af3_inference_native.pbs`, *not*
   `03_af3_inference_batched.pbs`, which is the one that produced the broken run.
   (`03b` runs the same fixed job through a Singularity container, but the container image
   is gone from scratch, so `03c` is the one that works today.) Until this is done, the AF3
   result isn't really a result.
2. **Finish the ESMFold diagnostic.** A few hours, and it's a correctness question rather
   than a research one — the script is written, it just needs running and reading. Given
   what the MSA problem turned out to be, I'd want to rule out a similar confidence-
   averaging bug before trusting any pLDDT number in this project.
3. **Run ProGen3 on the Konermann orthologs.** Completely unrun, everything's in place,
   and it's a self-contained result.
4. **Add the oracle scores as extra features to TIGER** rather than testing them alone.
   "Does this metric rank guides by itself?" is answered — no. "Does it add anything to a
   model that already works?" is the better question and I never got to it.

Reasoning for all of these, plus the things I'd actively avoid repeating, is in
[`docs/05_next_steps.md`](docs/05_next_steps.md).

---

## 7. One thing to deal with immediately

There's a **Hugging Face access token sitting in plaintext** in the original working copy of
the project, in `URECA_Code/boltz/download_results_from_hf.py` and `upload_to_hf.py`. I've
stripped it out of everything in this repo, but the originals still have it.

**Please revoke it** at https://huggingface.co/settings/tokens before you share that folder
with anyone or put it on GitHub. Instructions for setting up your own token properly are in
[`code/README.md`](code/README.md).
