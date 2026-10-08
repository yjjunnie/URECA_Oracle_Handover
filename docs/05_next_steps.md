# 05 — What Can Be Continued

Ranked by value per unit effort. Rationale given for each, so you can disagree with the
ordering on grounds rather than guesswork.

---

## Tier 1 — do these first

### 1.1 Finish the ESMFold pLDDT diagnostic
**Effort: hours. Value: high — it is a correctness blocker.**

`esmfold_test/00_diagnose_plddt.{py,pbs}` is written but has no results file, so it looks
never to have been run to conclusion. The pipeline reported ~30 average pLDDT on natural
proteins, which is implausible.

```bash
scp -O 00_diagnose_plddt.py hzhang08@aspire2.nscc.sg:/scratch/users/ntu/hzhang08/
qsub 00_diagnose_plddt.pbs
cat /scratch/users/ntu/hzhang08/logs/esmfold_diag.out
```

Read statistic **A** (`out["mean_plddt"]`) for ubiquitin:
- **A ≈ 85–95** → pipeline is healthy; the "30" came from reading statistic B/C/D (naive
  mean over all 37 atom slots) or from batch padding. Fix the aggregation and ESMFold
  becomes usable.
- **A ≈ 30** → weights, dtype, or truncation is broken. Nothing ESMFold produced is
  meaningful until fixed.

This is also the cheapest available test of whether the AF3 pLDDT ≈ 30 result shares a
cause — if a known-good protein scores ~30 in this stack too, it points at a systematic
aggregation bug rather than a biological conclusion, and would partially reopen
`04_results.md`. **That possibility is why this is task #1.**

### 1.2 Run ProGen3 on the Konermann Cas13d orthologs
**Effort: 1–2 days. Value: high — a complete, unrun experiment with everything in place.**

The environment works, the scripts work, the data exists, and it has never been run.

- Input: `[Konermann 2023] Cas13d ortholog sequences.csv` — 52 orthologs with sequences
- Convert to FASTA, score with `progen3-main/nscc_score_job.sh`
- Test: does log-likelihood / perplexity separate functional orthologs from
  non-functional ones? Konermann's paper reports which orthologs were active in human
  cells — use that as the label.
- Use the **3B** checkpoint: the published scaling curve is flat past 3B (ρ 0.35–0.40),
  so larger models buy nothing and cost VRAM.

Expect a coarse filter, not a precise predictor — that is what ρ ≈ 0.35–0.40 on
ProteinGym means. Framed as "can it reject implausible orthologs", it is still useful for
narrowing a wet-lab ortholog search.

### 1.3 Consolidate the two `tiger-main` copies
**Effort: an hour. Value: moderate — removes a standing trap.**

`tiger-main/tiger_full/` and `tiger-main/tiger-main/` are near-duplicates diverging in
Windows setup files. Keep one (the `tiger-main/tiger-main/` copy has the working install),
delete the other, delete the committed `tiger_env/` venv and `__pycache__/`, and record in
a README which upstream commit it came from. Also remove the stray `tiger-main/nul` file
(an artifact of a Windows redirect typo — `> nul` instead of `> /dev/null`).

---

## Tier 2 — the strongest scientific threads

### 2.1 Add oracle scores as features to TIGER
**Effort: 1–2 weeks. Value: highest scientific upside.**

This is the experiment the project was building toward and never reached.

Correlation asks "does this metric alone rank guides?" — answered, no. The better question
is **"does this metric add anything to a model that already works?"** TIGER is strong
(AUROC 0.86–0.95) and already uses `mfe`/`log_unpaired`. Take `tiger_trainer.py`, add
Boltz ipTM (and any ProGen3 score) as an extra input feature, retrain, and compare held-out
performance against the unmodified baseline.

Why it is still worth doing after a null correlation: features can be useless alone and
useful in combination. Honest expectation given the partial-correlation result in
`04_results.md` — which showed no incremental signal over the thermodynamic baselines —
is that this will also come out null. **But a null here is a much stronger and more
publishable claim**, because it tests the incremental question directly rather than by
proxy, and TIGER's established baseline makes the comparison credible.

Do it on the TIGER gene-holdout split, not a random split, or you will leak.

### 2.2 Establish whether the complexes are modellable at all
**Effort: days. Value: high — it decides whether 2.1 and all structural work is worth it.**

`04_results.md` cannot distinguish "confidence doesn't predict activity" from "AF3 can't
model these complexes" (pLDDT ≈ 30 for everything). Settle it:

- Fold a Cas13 complex with a **published experimental structure** (several Cas13a/Cas13b
  cryo-EM structures exist in the PDB) and compare predicted vs actual. If the predictor
  cannot reproduce a known Cas13 complex, that is the finding, and it fully explains the
  null result.
- Check whether pLDDT ≈ 30 persists when the **target RNA chain is removed** (protein +
  crRNA only). Single-stranded target RNA is the least modellable component; if the
  binary complex is confident and the ternary is not, that localises the failure.
- Try Boltz-2 with more `--recycling_steps` and `--diffusion_samples` (both were at the
  minimum: 3 and 1). Low sampling may itself be suppressing confidence.

This is the honest next move on the structural question. Do it before investing in 2.3.

### 2.3 Replicate on a model that handles protein–RNA better
**Effort: 1–2 weeks. Value: moderate, conditional on 2.2.**

Only worth it if 2.2 shows the complexes are modellable in principle. Candidates:
newer Boltz releases, RoseTTAFold2NA, or any protein–RNA-specialised predictor released
since. Reuse `boltz/` wholesale — swap the inference call, keep `generate_yamls.py`, the
manifest pattern and `04b_analyze_balanced.py` unchanged. That is the payoff of the
pipeline structure.

### 2.4 Power the balanced analysis properly
**Effort: days (mostly GPU time). Value: moderate.**

The balanced design is sound but *n* = 85 per protein. It rules out a strong effect, not a
weak one. With Boltz-2 being cheap, push to 500+ per protein. The DjCas13d ceiling of 85
guides is the real constraint — either accept unequal *n* with explicit power reporting,
or source more DjCas13d data.

Also: apply **multiple-comparison correction**. The current tables report 36–48 raw
p-values with no FDR control. Nothing survives anyway, so the conclusion is unchanged, but
the tables should not be published as-is.

---

## Tier 3 — opportunistic

### 3.1 Use the Nucleaseq dataset
`[Nucleaseq] Supplemental_File_1.xlsx` is unused. It offers quantitative SpCas9 cleavage
*kinetics* rather than pooled-screen readouts — a cleaner, less noisy label. If the
hypothesis is ever retested, a kinetic label is a better target than a survival ratio.

### 3.2 Off-target prediction
`tiger-main/tiger_full/off-target/` and the `SM` (single-mismatch) rows in the TIGER data
are untouched. Mismatch tolerance is arguably a *better* fit for structural methods than
on-target activity: a mismatch produces a concrete, local structural perturbation that a
folding model might actually resolve, whereas on-target activity depends on kinetics and
cellular context a static structure cannot see. Given the on-target null, this is the more
defensible structural question.

### 3.3 LinearFold properly
LinearFold features were used as pre-computed columns from the TIGER dataset; LinearFold
itself was never run. If you need features for *new* guides not in the TIGER data, you will
have to run it — its O(n) scaling makes genome-wide feature generation practical where
Vienna/CONTRAfold would not be.

### 3.4 Document the AF3 MSA work
`build_casrx_msa.py`, `casrx_orthologs.a3m` and `fix_rna_pairedmsa.py` encode real
hard-won knowledge about getting AF3 to accept a custom Cas13d MSA, and that is nowhere
written down. If anyone revisits AF3, this will be re-derived expensively. A short note in
`my_parts/` would prevent that.

---

## Explicitly not worth repeating

- **Re-running AF3 or Boltz-2 confidence vs activity correlation as-is.** Two models,
  three proteins, ~1,800 complexes, balanced design. Answered. Change the question
  (2.1, 2.2, 3.2) rather than re-asking it.
- **Requesting AF3 weights for a fresh start.** Boltz-2 gives the same answer and installs
  with `pip`. Only go back to AF3 if you specifically need its genetic-database MSA
  pipeline.
- **Scaling ProGen3 past 3B.** The scaling curve is flat; it costs VRAM and buys nothing.

---

## Known debts

- Large binaries sitting in the working tree: `boltz2_conf.ckpt` (2.29 GB), `mols.tar`
  (1.86 GB), `af3.bin.zst`, `flash_attn.whl`, `hugging_face.zip`, `tiger_env/`.
  None belong in version control. `.gitignore` here covers these patterns.
- `__pycache__/` committed under `tiger-main/tiger_full/`.
- Hardcoded absolute paths (`/scratch/users/ntu/hzhang08`, `c:\Users\holly\...`) throughout
  the scripts. The templates here use a `SCRATCH` variable instead — worth retrofitting.
- `af3_tiger_research_plan.docx` in `my_parts/` is the original plan; it has not been
  reconciled with what was actually found, and is not a reliable description of the
  project's current state. Treat `04_results.md` as authoritative.
