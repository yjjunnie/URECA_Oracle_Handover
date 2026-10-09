#!/usr/bin/env python3
"""
04_analyze.py
=============
Parse Boltz-2 confidence JSONs and correlate with guide activity.

Mirrors the AF3 analysis approach:
  Stage 1 – Spearman + Pearson correlations per dataset per metric
  Stage 2 – Heatmap (Spearman ρ) across datasets × metrics
  Stage 3 – Scatter plots for top metric per dataset

Activity direction:
  tiger_fc / tiger_ht : mean_lfc           (used as-is)
  konermann_*         : mean_rel_expr      (negated: lower expr = more active)
  azimuth_v1          : mean_screen_activity (used as-is)

Run after 03_boltz_batch.pbs finishes:
  python 04_analyze.py

Outputs in $SCRATCH/boltz_analysis_results/:
  boltz_confidence_scores.csv   -- raw per-guide scores
  correlations.csv              -- Spearman + Pearson per metric per dataset
  correlation_heatmap.png       -- Spearman ρ heatmap
  scatter_{top_metric}.png      -- scatter plots per dataset
"""

import os
import json
import glob
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

SCRATCH     = "/scratch/users/ntu/hzhang08"
MANIFEST    = f"{SCRATCH}/yamls_fullprot/manifest.tsv"
BOLTZ_OUT   = f"{SCRATCH}/boltz_out_fullprot"
RESULTS_DIR = f"{SCRATCH}/boltz_analysis_results_fullprot"
os.makedirs(RESULTS_DIR, exist_ok=True)


# ── Index confidence JSONs ────────────────────────────────────────────────────
print("Indexing confidence JSONs …", flush=True)
stem_to_json = {}
for path in glob.glob(f"{BOLTZ_OUT}/**/confidence_*_model_0.json", recursive=True):
    fname = os.path.basename(path)
    stem  = fname.replace("confidence_", "").replace("_model_0.json", "")
    stem_to_json[stem] = path

print(f"  Found {len(stem_to_json)} confidence JSONs", flush=True)


# ── Parse JSONs ───────────────────────────────────────────────────────────────
manifest = pd.read_csv(MANIFEST, sep="\t")
rows, missing = [], []

for _, row in manifest.iterrows():
    stem = os.path.splitext(os.path.basename(row["yaml_path"]))[0]
    path = stem_to_json.get(stem)
    if path is None:
        missing.append(stem)
        continue

    with open(path) as fh:
        c = json.load(fh)

    pci = c.get("pair_chains_iptm", {})

    def avg_pair(i, j):
        a = pci.get(str(i), {}).get(str(j), np.nan)
        b = pci.get(str(j), {}).get(str(i), np.nan)
        vals = [v for v in [a, b] if not np.isnan(v)]
        return float(np.mean(vals)) if vals else np.nan

    cptm = c.get("chains_ptm", {})

    rows.append({
        "dataset":           row["dataset"],
        "guide_id":          row["guide_id"],
        "guide_seq":         row["guide_seq"],
        "activity":          row["activity"],
        "activity_label":    row["activity_label"],
        # Global metrics
        "confidence_score":  c.get("confidence_score"),
        "ptm":               c.get("ptm"),
        "iptm":              c.get("iptm"),
        "complex_plddt":     c.get("complex_plddt"),
        "complex_iplddt":    c.get("complex_iplddt"),
        "complex_pde":       c.get("complex_pde"),
        "complex_ipde":      c.get("complex_ipde"),
        # Per-chain ptm (chains: 0=protein, 1=gRNA, 2=target)
        "ptm_protein":       cptm.get("0"),
        "ptm_grna":          cptm.get("1"),
        "ptm_target":        cptm.get("2"),
        # Pairwise interface iptm (averaged over both directions)
        "iptm_prot_grna":    avg_pair(0, 1),
        "iptm_grna_target":  avg_pair(1, 2),
        "iptm_prot_target":  avg_pair(0, 2),
    })

df = pd.DataFrame(rows)
df.to_csv(f"{RESULTS_DIR}/boltz_confidence_scores.csv", index=False)
print(f"\nParsed {len(df)}/{len(manifest)} guides  ({len(missing)} missing)", flush=True)
if missing:
    print(f"  First 5 missing: {missing[:5]}")


# ── Correlation helpers ───────────────────────────────────────────────────────
METRICS = [
    "confidence_score", "ptm", "iptm",
    "complex_plddt", "complex_iplddt",
    "complex_pde", "complex_ipde",
    "ptm_grna", "ptm_target",
    "iptm_prot_grna", "iptm_grna_target", "iptm_prot_target",
]

def spearman_pearson(x, y):
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(valid) < 10:
        return np.nan, np.nan, np.nan, np.nan, len(valid)
    sp_r, sp_p = stats.spearmanr(valid["x"], valid["y"])
    pe_r, pe_p = stats.pearsonr(valid["x"],  valid["y"])
    return float(sp_r), float(sp_p), float(pe_r), float(pe_p), len(valid)

def sig_flag(p):
    if np.isnan(p): return ""
    if p < 0.001:   return " ***"
    if p < 0.01:    return " **"
    if p < 0.05:    return " *"
    return ""


# ── Stage 1: per-dataset correlations ─────────────────────────────────────────
print("\n" + "=" * 80)
print("STAGE 1: SPEARMAN + PEARSON CORRELATIONS PER DATASET")
print("=" * 80)

records = []
for dataset, grp in df.groupby("dataset"):
    activity = grp["activity"].copy()
    label    = grp["activity_label"].iloc[0]
    if label == "mean_rel_expr":
        activity = -activity   # lower expr = more active → negate for consistency

    print(f"\n── {dataset}  (n={len(grp)}, activity={label}) ──")
    print(f"  {'Metric':<22} {'Spearman r':>11} {'p':>10} {'Pearson r':>10} {'p':>10}  n")
    print(f"  {'-'*22} {'-'*11} {'-'*10} {'-'*10} {'-'*10} {'-'*5}")

    for metric in METRICS:
        if metric not in grp.columns:
            continue
        sp_r, sp_p, pe_r, pe_p, n = spearman_pearson(grp[metric], activity)
        if np.isnan(sp_r):
            continue
        flag = sig_flag(sp_p)
        print(f"  {metric:<22} {sp_r:>+11.4f} {sp_p:>10.3e} {pe_r:>+10.4f} {pe_p:>10.3e}  {n}{flag}")
        records.append({
            "dataset":     dataset,
            "activity":    label,
            "metric":      metric,
            "spearman_r":  sp_r, "spearman_p": sp_p,
            "pearson_r":   pe_r, "pearson_p":  pe_p,
            "n":           n,
        })

corr_df = pd.DataFrame(records)
corr_df.to_csv(f"{RESULTS_DIR}/correlations.csv", index=False)
print(f"\nCorrelations saved: {RESULTS_DIR}/correlations.csv")
print("Significance: * p<0.05  ** p<0.01  *** p<0.001")


# ── Stage 2: heatmap ──────────────────────────────────────────────────────────
pivot = corr_df.pivot(index="metric", columns="dataset", values="spearman_r")

fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 2), len(pivot) * 0.7 + 1.5))
sns.heatmap(
    pivot, annot=True, fmt=".2f", cmap="RdBu_r",
    center=0, vmin=-0.5, vmax=0.5, linewidths=0.5, ax=ax,
    annot_kws={"size": 9},
)
ax.set_title("Boltz-2 confidence vs guide activity  (Spearman ρ)", fontsize=13)
ax.set_xlabel("Dataset", fontsize=11)
ax.set_ylabel("Boltz-2 metric", fontsize=11)
plt.tight_layout()
heatmap_path = f"{RESULTS_DIR}/correlation_heatmap.png"
fig.savefig(heatmap_path, dpi=150)
plt.close()
print(f"\nHeatmap saved: {heatmap_path}")


# ── Stage 3: scatter plots for top metric ────────────────────────────────────
best_row    = corr_df.loc[corr_df["spearman_r"].abs().idxmax()]
best_metric = best_row["metric"]
print(f"\nTop metric overall: {best_metric}  (|ρ| = {abs(best_row['spearman_r']):.3f}, "
      f"dataset={best_row['dataset']})")

datasets = sorted(df["dataset"].unique())
ncols = min(len(datasets), 3)
nrows = (len(datasets) + ncols - 1) // ncols
fig2, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)
axes = axes.flatten()

for i, dataset in enumerate(datasets):
    ax  = axes[i]
    grp = df[df["dataset"] == dataset]
    activity = grp["activity"].copy()
    if grp["activity_label"].iloc[0] == "mean_rel_expr":
        activity = -activity

    valid = grp[best_metric].notna()
    ax.scatter(grp.loc[valid, best_metric], activity[valid],
               alpha=0.4, s=15, edgecolors="none")

    # regression line
    x = grp.loc[valid, best_metric].values
    y = activity[valid].values
    if len(x) > 5:
        z = np.polyfit(x, y, 1)
        xr = np.linspace(x.min(), x.max(), 100)
        ax.plot(xr, np.polyval(z, xr), "k--", lw=1, alpha=0.5)

    sp_r, sp_p, _, _, n = spearman_pearson(grp[best_metric], activity)
    ax.set_title(f"{dataset}\nρ = {sp_r:+.3f}, p = {sp_p:.2e}  (n={n})", fontsize=9)
    ax.set_xlabel(best_metric, fontsize=8)
    ax.set_ylabel("activity (higher = more active)", fontsize=8)

for ax in axes[len(datasets):]:
    ax.set_visible(False)

plt.suptitle(f"Boltz-2  {best_metric}  vs guide activity", fontsize=12)
plt.tight_layout()
scatter_path = f"{RESULTS_DIR}/scatter_{best_metric}.png"
fig2.savefig(scatter_path, dpi=150)
plt.close()
print(f"Scatter plots saved: {scatter_path}")


# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SUMMARY — top 5 metrics by |Spearman ρ| (averaged across datasets)")
print("=" * 80)
summary = (
    corr_df.groupby("metric")["spearman_r"]
    .apply(lambda x: x.abs().mean())
    .sort_values(ascending=False)
    .head(5)
)
for metric, mean_abs_rho in summary.items():
    row = corr_df[corr_df["metric"] == metric].sort_values("spearman_r", key=abs, ascending=False).iloc[0]
    print(f"  {metric:<25} mean|ρ|={mean_abs_rho:.3f}   best: {row['dataset']} ρ={row['spearman_r']:+.3f}{sig_flag(row['spearman_p'])}")

print(f"\nAll results in: {RESULTS_DIR}/")
