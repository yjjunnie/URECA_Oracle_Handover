# NOTE: This is the version that actually produced the committed results in
# results/alphafold3/. It was recovered from write_analyze_final.pbs, a job that
# wrote it to disk via heredoc. An alternative refactor existed alongside it but
# was broken: it merged on a "quartile" column while plotting on "quintile", and
# it parsed chain_pair_iptm as a dict of dicts when AF3 emits a 2D array, so it
# produced no chain_iptm_* values. That refactor did contain one unfinished good
# idea - partial correlation against SEVERAL baselines jointly, not one at a time.
# Worth redoing if you extend this.

"""
analyze_af3_results.py
======================
Parses AF3 output files, extracts confidence scores, and correlates
them with TIGER LFC values to test whether structural confidence
predicts Cas13d guide RNA knockdown activity.

Run after AF3 inference jobs are complete on NSCC.

Usage:
    python analyze_af3_results.py \
        --af3_dir   /scratch/users/ntu/<YOUR_NSCC_ID>/af3_outputs_final \
        --metadata  /scratch/users/ntu/<YOUR_NSCC_ID>/tiger_af3_full_complex_sample.csv \
        --output_dir /scratch/users/ntu/<YOUR_NSCC_ID>/results/

Output files:
    af3_lfc_merged.csv       - merged AF3 scores + LFC values per guide
    correlations.csv         - Spearman/Pearson r for each metric vs LFC
    partial_correlations.csv - partial r after controlling for thermodynamics
    af3_lfc_correlations.png - scatter plots (requires matplotlib)

AF3 output structure expected (one folder per guide):
    af3_outputs_final/
        UID_032743_lfcn0p218/
            UID_032743_lfcn0p218_summary_confidences_0.json   <- ipTM, pTM
            UID_032743_lfcn0p218_confidences_0.json           <- per-residue pLDDT, PAE
            UID_032743_lfcn0p218_model_0.cif                  <- 3D structure

Key metrics extracted:
    ipTM        - interface predicted TM-score (primary: protein:crRNA:target interface)
    pTM         - overall complex TM-score
    ranking_score - AF3 combined confidence score
    mean_plddt  - mean per-residue confidence across all chains
    plddt_chain_A - mean pLDDT on CasRx protein chain
    plddt_chain_B - mean pLDDT on crRNA (DR + spacer)
    plddt_chain_C - mean pLDDT on target RNA
    plddt_DR    - mean pLDDT on direct repeat residues (nt 1-30 of chain B)
    plddt_spacer - mean pLDDT on spacer residues (nt 31-53 of chain B)
    iptm_AB     - interface pTM between protein (A) and crRNA (B)
    iptm_BC     - interface pTM between crRNA (B) and target (C)
    iptm_AC     - interface pTM between protein (A) and target (C)

Statistical analysis:
    Stage 1: Spearman + Pearson correlation (each metric vs LFC)
    Stage 2: Partial correlation controlling for hybrid_mfe
             (does AF3 add info beyond thermodynamics?)
    Stage 3: Summary table with significance flags
"""

import os
import json
import glob
import argparse
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from numpy.linalg import lstsq

warnings.filterwarnings("ignore")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False
    print("matplotlib not available - skipping plots (install with: pip install matplotlib)")


# - Constants -

# Chain assignments (as defined in af3_inputs_v2 JSONs)
CHAIN_PROTEIN = "A"   # RfxCas13d
CHAIN_CRRNA   = "B"   # crRNA: 30 nt DR + 23 nt spacer = 53 nt total
CHAIN_TARGET  = "C"   # target RNA: 23 nt

DR_LENGTH     = 30    # direct repeat nucleotides in chain B
SPACER_LENGTH = 23    # spacer nucleotides in chain B (positions 31-53)


# - Parsing -

def parse_summary_confidences(path):
    """
    Extract top-level scores from summary_confidences_*.json.

    AF3 summary confidence keys:
        ptm           - overall predicted TM-score
        iptm          - interface predicted TM-score
        ranking_score - combined confidence (0.8*iptm + 0.2*ptm)
        chain_ptm     - list of per-chain pTM scores
        chain_iptm    - list of per-chain ipTM scores (order = chain order in input)
    """
    with open(path) as f:
        sc = json.load(f)

    out = {
        "ptm":           sc.get("ptm",           np.nan),
        "iptm":          sc.get("iptm",          np.nan),
        "ranking_score": sc.get("ranking_score", np.nan),
    }

    # Per-chain pTM (list, ordered by chain A/B/C)
    chain_ptm = sc.get("chain_ptm", [])
    if len(chain_ptm) >= 3:
        out["chain_ptm_A"] = chain_ptm[0]   # protein
        out["chain_ptm_B"] = chain_ptm[1]   # crRNA
        out["chain_ptm_C"] = chain_ptm[2]   # target

    # chain_pair_iptm: 2D array [num_chains x num_chains]
    # Chain order: A=0 (protein), B=1 (crRNA), C=2 (target)
    cpi = sc.get("chain_pair_iptm", [])
    try:
        cpi = np.array(cpi)
        if cpi.ndim == 2 and cpi.shape[0] >= 3:
            out["iptm_AB"] = float(cpi[0][1])
            out["iptm_AC"] = float(cpi[0][2])
            out["iptm_BC"] = float(cpi[1][2])
        else:
            out["iptm_AB"] = out["iptm_AC"] = out["iptm_BC"] = np.nan
    except Exception:
        out["iptm_AB"] = out["iptm_AC"] = out["iptm_BC"] = np.nan

    chain_iptm = sc.get("chain_iptm", [])
    try:
        if len(chain_iptm) >= 3:
            out["chain_iptm_A"] = float(chain_iptm[0])
            out["chain_iptm_B"] = float(chain_iptm[1])
            out["chain_iptm_C"] = float(chain_iptm[2])
    except Exception:
        pass

    return out


def parse_confidences(path):
    """
    Extract per-residue pLDDT and chain-level averages from confidences_*.json.

    AF3 confidences keys:
        atom_plddts    - per-atom pLDDT values (0-100)
        atom_chain_ids - chain ID for each atom (A/B/C)
        atom_res_ids   - residue index for each atom (1-based)
        pae            - predicted aligned error matrix (optional, large)
    """
    with open(path) as f:
        conf = json.load(f)

    out = {}

    plddt     = np.array(conf.get("atom_plddts",    []))
    chain_ids = np.array(conf.get("atom_chain_ids", []))
    res_ids   = np.array(conf.get("atom_res_ids",   []))

    if len(plddt) == 0:
        return out

    # Whole complex mean
    out["mean_plddt"] = float(np.mean(plddt))

    # Per-chain means
    for chain, label in [
        (CHAIN_PROTEIN, "plddt_chain_A"),
        (CHAIN_CRRNA,   "plddt_chain_B"),
        (CHAIN_TARGET,  "plddt_chain_C"),
    ]:
        mask = chain_ids == chain
        if mask.any():
            out[label] = float(np.mean(plddt[mask]))

    # crRNA sub-regions (chain B)
    mask_B = chain_ids == CHAIN_CRRNA
    if mask_B.any() and len(res_ids) > 0:
        # Direct repeat: residues 1 to DR_LENGTH
        dr_mask = mask_B & (res_ids >= 1) & (res_ids <= DR_LENGTH)
        if dr_mask.any():
            out["plddt_DR"] = float(np.mean(plddt[dr_mask]))

        # Spacer: residues DR_LENGTH+1 to DR_LENGTH+SPACER_LENGTH
        sp_mask = mask_B & (res_ids > DR_LENGTH) & (res_ids <= DR_LENGTH + SPACER_LENGTH)
        if sp_mask.any():
            out["plddt_spacer"] = float(np.mean(plddt[sp_mask]))

    return out


def parse_one_job(job_dir):
    """Parse all AF3 outputs for a single guide job directory."""
    job_name = os.path.basename(job_dir)
    result   = {"job_name": job_name}

    # Find summary_confidences file (AF3 names it with seed index, e.g. _0)
    sc_files = glob.glob(os.path.join(job_dir, "*summary_confidences*.json"))
    if sc_files:
        result.update(parse_summary_confidences(sc_files[0]))
    else:
        print(f"  WARNING: No summary_confidences file in {job_name}")

    # Find confidences file
    conf_files = glob.glob(os.path.join(job_dir, "*confidences*.json"))
    # Exclude summary_confidences (already handled above)
    conf_files = [f for f in conf_files if "summary" not in os.path.basename(f)]
    if conf_files:
        try:
            result.update(parse_confidences(conf_files[0]))
        except Exception as e:
            print(f"  WARNING: Could not parse confidences for {job_name}: {e}")

    return result


def parse_all_jobs(af3_dir):
    """Walk af3_dir and parse every job subdirectory."""
    # Each job is a subdirectory named after the guide
    job_dirs = [
        d for d in sorted(glob.glob(os.path.join(af3_dir, "*")))
        if os.path.isdir(d)
    ]

    if not job_dirs:
        # Try flat structure (all files in one directory)
        sc_files = glob.glob(os.path.join(af3_dir, "*summary_confidences*.json"))
        if sc_files:
            print(f"Found {len(sc_files)} summary files in flat directory structure")
            records = []
            for f in sc_files:
                job_name = os.path.basename(f).replace("_summary_confidences_0.json", "")
                rec = {"job_name": job_name}
                rec.update(parse_summary_confidences(f))
                conf_f = f.replace("summary_confidences", "confidences")
                if os.path.exists(conf_f):
                    try:
                        rec.update(parse_confidences(conf_f))
                    except Exception as e:
                        print(f"  WARNING: {job_name} confidences: {e}")
                records.append(rec)
            return pd.DataFrame(records)
        else:
            print(f"ERROR: No AF3 output directories or files found in {af3_dir}")
            return pd.DataFrame()

    print(f"Found {len(job_dirs)} job directories")
    records = []
    for d in job_dirs:
        try:
            records.append(parse_one_job(d))
        except Exception as e:
            print(f"  ERROR parsing {os.path.basename(d)}: {e}")

    return pd.DataFrame(records)


# - Metadata matching -

def match_metadata(af3_df, metadata_path):
    """
    Match AF3 results back to TIGER metadata using job name.

    Job names were generated as: {guide_id}_lfc{lfc_encoded}
    e.g. UID_032743_lfcn0p218 -> guide_id = UID_032743
    """
    meta = pd.read_csv(metadata_path)
    print(f"\nMetadata: {len(meta)} guides")
    print(f"AF3 results: {len(af3_df)} guides")

    # Job names: casrx_UID_033127_DIMT1 -> guide_id = UID_033127
    def extract_id(job_name):
        s = str(job_name)
        if s.startswith("casrx_"):
            s = s[len("casrx_"):]
        parts = s.split("_")
        if len(parts) >= 2 and parts[0] == "UID":
            return f"UID_{parts[1]}"
        return s

    af3_df = af3_df.copy()
    af3_df["guide_id_match"] = af3_df["job_name"].apply(extract_id)

    # Identify available baseline columns in metadata
    baseline_cols = [
        c for c in ["hybrid_mfe", "hybrid_mfe_1_23", "hybrid_mfe_15_9",
                    "log_unpaired", "mfe", "guide_fold", "target_fold"]
        if c in meta.columns
    ]

    merge_cols = ["guide_id", "mean_lfc", "quintile"] + baseline_cols
    merge_cols = [c for c in merge_cols if c in meta.columns]

    merged = af3_df.merge(
        meta[merge_cols],
        left_on="guide_id_match",
        right_on="guide_id",
        how="inner"
    )

    print(f"Matched: {len(merged)} / {len(af3_df)}")
    if len(merged) < len(af3_df) * 0.8:
        print("WARNING: <80% matched - check job name format vs guide_id format")
        print(f"  Sample job names: {af3_df['job_name'].head(3).tolist()}")
        print(f"  Sample guide IDs: {meta['guide_id'].head(3).tolist()}")

    return merged, baseline_cols


# - Statistical analysis -

def spearman_pearson(x, y):
    valid = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(valid) < 10:
        return np.nan, np.nan, np.nan, np.nan
    sp_r, sp_p = stats.spearmanr(valid["x"], valid["y"])
    pe_r, pe_p = stats.pearsonr(valid["x"],  valid["y"])
    return float(sp_r), float(sp_p), float(pe_r), float(pe_p)


def partial_correlation(df, metric, baseline, outcome="mean_lfc"):
    """
    Spearman partial correlation: metric vs outcome, controlling for baseline.

    Method: residualise both metric and outcome on baseline, then correlate.
    Tests whether AF3 metric adds predictive power beyond thermodynamic baseline.
    """
    cols = [metric, baseline, outcome]
    valid = df[cols].dropna()
    if len(valid) < 20:
        return np.nan, np.nan, len(valid)

    X = np.column_stack([valid[baseline].values, np.ones(len(valid))])

    resid_metric  = valid[metric].values  - X @ lstsq(X, valid[metric].values,  rcond=None)[0]
    resid_outcome = valid[outcome].values - X @ lstsq(X, valid[outcome].values, rcond=None)[0]

    r, p = stats.spearmanr(resid_metric, resid_outcome)
    return float(r), float(p), len(valid)


def run_correlations(df, baseline_cols):
    """Stage 1: raw correlations of all AF3 metrics with LFC."""
    af3_metrics = [
        "ptm", "iptm", "ranking_score",
        "mean_plddt", "plddt_chain_A", "plddt_chain_B", "plddt_chain_C",
        "plddt_DR", "plddt_spacer",
        "iptm_AB", "iptm_AC", "iptm_BC",
        "chain_ptm_A", "chain_ptm_B", "chain_ptm_C",
    ]

    print("\n" + "=" * 70)
    print("STAGE 1: RAW CORRELATIONS WITH MEAN LFC")
    print("=" * 70)
    print(f"\n{'Metric':<25} {'Spearman r':>12} {'p-value':>12} {'Pearson r':>12} {'n':>6}")
    print("-" * 70)

    records = []
    for col in af3_metrics + baseline_cols:
        if col not in df.columns:
            continue
        valid_n = df[[col, "mean_lfc"]].dropna().__len__()
        sp_r, sp_p, pe_r, pe_p = spearman_pearson(df[col], df["mean_lfc"])
        if np.isnan(sp_r):
            continue
        sig = " *" if sp_p < 0.05 else ("  " if sp_p < 0.1 else "")
        tag = " [baseline]" if col in baseline_cols else ""
        print(f"  {col+tag:<23} {sp_r:>12.4f} {sp_p:>12.4e} {pe_r:>12.4f} {valid_n:>6}{sig}")
        records.append({
            "metric": col, "is_baseline": col in baseline_cols,
            "spearman_r": sp_r, "spearman_p": sp_p,
            "pearson_r":  pe_r, "pearson_p":  pe_p,
            "n": valid_n,
        })

    return pd.DataFrame(records)


def run_partial_correlations(df, baseline_cols):
    """
    Stage 2: partial correlations - AF3 metrics controlling for thermodynamics.

    Key question: does ipTM predict LFC beyond what hybrid_mfe already knows?
    High partial r = AF3 captures geometry that thermodynamics misses.
    Low partial r = AF3 and thermodynamics are redundant (same underlying signal).
    """
    af3_metrics = ["ptm", "iptm", "ranking_score", "mean_plddt",
                   "plddt_DR", "plddt_spacer", "iptm_AB", "iptm_BC"]

    print("\n" + "=" * 70)
    print("STAGE 2: PARTIAL CORRELATIONS (AF3 controlling for thermodynamics)")
    print("=" * 70)
    print("Tests whether AF3 adds predictive power BEYOND existing features.")
    print("High partial r = AF3 captures structural information thermodynamics misses.")
    print(f"\n{'AF3 metric':<20} {'Baseline':<25} {'Partial r':>10} {'p-value':>12} {'n':>6}")
    print("-" * 70)

    records = []
    for m in af3_metrics:
        if m not in df.columns:
            continue
        for b in baseline_cols:
            if b not in df.columns:
                continue
            r, p, n = partial_correlation(df, m, b)
            if np.isnan(r):
                continue
            sig = " *" if p < 0.05 else ""
            print(f"  {m:<18} {b:<25} {r:>10.4f} {p:>12.4e} {n:>6}{sig}")
            records.append({
                "af3_metric": m, "baseline": b,
                "partial_r": r, "partial_p": p, "n": n,
            })

    return pd.DataFrame(records)


# - Plotting -

def plot_scatter(df, output_dir):
    if not HAS_PLOT:
        return

    metrics = [m for m in ["iptm", "ptm", "mean_plddt", "plddt_spacer", "iptm_AB"]
               if m in df.columns and df[m].notna().sum() > 5]

    if not metrics:
        print("No plottable metrics found")
        return

    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 5))
    if len(metrics) == 1:
        axes = [axes]

    colors = {0: "#d62728", 1: "#ff7f0e", 2: "#2ca02c",
              3: "#1f77b4", 4: "#9467bd"}

    for ax, metric in zip(axes, metrics):
        valid = df[[metric, "mean_lfc", "quintile"]].dropna()
        for q, grp in valid.groupby("quintile"):
            ax.scatter(grp[metric], grp["mean_lfc"],
                       alpha=0.6, s=20, color=colors.get(q, "gray"), label=str(q))

        # Regression line
        if len(valid) > 5:
            m_vals = valid[metric].values
            y_vals = valid["mean_lfc"].values
            try:
                z = np.polyfit(m_vals, y_vals, 1)
                p_line = np.poly1d(z)
                x_range = np.linspace(m_vals.min(), m_vals.max(), 100)
                ax.plot(x_range, p_line(x_range), "k--", alpha=0.4, lw=1)
            except Exception:
                pass

        sp_r, sp_p, _, _ = spearman_pearson(valid[metric], valid["mean_lfc"])
        ax.set_xlabel(metric, fontsize=11)
        ax.set_ylabel("Mean LFC", fontsize=11)
        ax.set_title(f"{metric} vs LFC\nSpearman r={sp_r:.3f}, p={sp_p:.2e}", fontsize=10)
        ax.legend(title="Quintile", fontsize=7, markerscale=1.5)

    plt.tight_layout()
    out = os.path.join(output_dir, "af3_lfc_correlations.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nScatter plot saved: {out}")
    plt.close()


# - Main -

def main():
    parser = argparse.ArgumentParser(description="Analyze AF3 outputs vs TIGER LFC")
    parser.add_argument("--af3_dir",    required=True, help="AF3 output directory")
    parser.add_argument("--metadata",   required=True, help="tiger_af3_full_complex_sample.csv")
    parser.add_argument("--output_dir", default="./af3_analysis", help="Results output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Parse AF3 outputs
    print("=" * 70)
    print("PARSING AF3 OUTPUTS")
    print("=" * 70)
    af3_df = parse_all_jobs(args.af3_dir)

    if af3_df.empty:
        print(f"\nERROR: No AF3 output files found in {args.af3_dir}")
        print("Expected structure:")
        print("  af3_dir/<job_name>/<job_name>_summary_confidences_0.json")
        return

    print(f"\nParsed {len(af3_df)} jobs")
    print("Available metrics:", [c for c in af3_df.columns if c != "job_name"])

    # 2. Match to metadata
    print("\n" + "=" * 70)
    print("MATCHING TO TIGER METADATA")
    print("=" * 70)
    merged, baseline_cols = match_metadata(af3_df, args.metadata)

    if merged.empty:
        print("ERROR: No guides matched - check job name format")
        return

    # Save merged data
    merged_path = os.path.join(args.output_dir, "af3_lfc_merged.csv")
    merged.to_csv(merged_path, index=False)
    print(f"Merged data saved: {merged_path}")

    # Describe LFC distribution
    print(f"\nLFC range: {merged['mean_lfc'].min():.3f} to {merged['mean_lfc'].max():.3f}")
    if "quintile" in merged.columns:
        print(merged.groupby("quintile")["mean_lfc"].agg(["count", "min", "mean", "max"]).round(3))

    # 3. Stage 1: raw correlations
    corr_df = run_correlations(merged, baseline_cols)
    corr_path = os.path.join(args.output_dir, "correlations.csv")
    corr_df.to_csv(corr_path, index=False)
    print(f"\nCorrelations saved: {corr_path}")

    # 4. Stage 2: partial correlations
    if baseline_cols:
        partial_df = run_partial_correlations(merged, baseline_cols)
        partial_path = os.path.join(args.output_dir, "partial_correlations.csv")
        partial_df.to_csv(partial_path, index=False)
        print(f"\nPartial correlations saved: {partial_path}")
    else:
        print("\nNo baseline thermodynamic columns found - skipping partial correlations")
        print("Expected columns: hybrid_mfe, log_unpaired, mfe")

    # 5. Plots
    plot_scatter(merged, args.output_dir)

    # 6. Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if not corr_df.empty:
        af3_corrs = corr_df[~corr_df["is_baseline"]].sort_values("spearman_r", key=abs, ascending=False)
        print("\nTop AF3 metrics by |Spearman r|:")
        for _, row in af3_corrs.head(5).iterrows():
            sig = " *" if row["spearman_p"] < 0.05 else ""
            print(f"  {row['metric']:<25} r={row['spearman_r']:+.4f}  p={row['spearman_p']:.3e}{sig}")

    print(f"\nAll results in: {args.output_dir}/")
    print("  af3_lfc_merged.csv        - merged AF3 scores + LFC")
    print("  correlations.csv          - Spearman/Pearson table")
    print("  partial_correlations.csv  - partial r controlling for thermodynamics")
    print("  af3_lfc_correlations.png  - scatter plots")


if __name__ == "__main__":
    main()
