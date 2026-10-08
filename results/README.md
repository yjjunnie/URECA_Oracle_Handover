# Results (copied in, so this repo stands alone)

These are the actual analysis outputs, copied from the working tree so the handover is
self-contained. Interpretation is in [`../docs/04_results.md`](../docs/04_results.md) —
read that first; these are the raw tables behind it.

```
boltz/                                 from URECA_Code/boltz/correlation_results/
├── boltz_confidence_scores.csv        per-guide: 12 metrics + activity, 4 datasets
├── correlations.csv                   Spearman + Pearson per dataset x metric (48 rows)
├── correlation_heatmap.png            rho heatmap, datasets x metrics
├── scatter_iptm_prot_target.png       best-metric scatter
└── balanced/                          THE TRUSTWORTHY ANALYSIS - 85 guides per Cas protein
    ├── boltz_confidence_scores_balanced.csv
    ├── correlations_balanced.csv      36 rows, not one significant
    ├── correlation_heatmap_balanced.png
    └── scatter_confidence_score_balanced.png

alphafold3/                            from alphafold3/my_parts/results/results/
├── af3_lfc_merged.csv                 per-guide: AF3 metrics + LFC + quintile + baselines
├── correlations.csv                   AF3 metrics AND thermodynamic baselines vs LFC
├── partial_correlations.csv           AF3 metrics after controlling for baselines
└── af3_lfc_correlations.png           scatter plots
```

## Reading guide

- **`alphafold3/correlations.csv`** is the single most informative file. The
  `is_baseline` column separates AF3 metrics (`False`) from thermodynamic baselines
  (`True`). The baselines win by 3–5×.
- **`alphafold3/partial_correlations.csv`** is the file that closes the argument: AF3
  metrics contribute nothing beyond the baselines.
- **`boltz/balanced/correlations_balanced.csv`** is the clean confirmatory test —
  protein-balanced, equal *n*, no significant result anywhere.
- Prefer `balanced/` over the unbalanced Boltz tables. The unbalanced pass confounds
  dataset with Cas protein and has unequal *n*; its few marginal p-values did not
  replicate.

## Not copied

- `.cif` structure files and renders — see
  `alphafold3/my_parts/results/cif_files/{top_ranked,bottom_ranked}/` in the working tree
  (5 structures from each activity extreme).
- Raw AF3/Boltz output directories, which lived on NSCC scratch and have likely been
  purged. The per-guide CSVs here are the durable record of them.
