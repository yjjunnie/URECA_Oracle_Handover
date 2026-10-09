#!/usr/bin/env python3
"""
build_casrx_msa.py
==================
Builds a query-anchored A3M alignment for the CasRx protein chain from the
Cas13d ortholog set in "[Konermann 2023] Cas13d ortholog sequences.csv",
so AF3 can be run with a supplied MSA instead of relying on its database
search.

Why: the previous 500-job run came back with mean pLDDT ~30, pTM 0.19,
ipTM 0.23 -- i.e. AF3 never folded CasRx. That is the signature of an
empty (not merely shallow) protein MSA. Rather than depend on AF3's
database search finding Cas13d homologs, this supplies 52 curated
orthologs directly.

Method: each ortholog is aligned to the CasRx query independently
(query-anchored pairwise alignment, BLOSUM62, free end gaps). This is the
alignment model A3M is designed around -- columns are defined by the
query, and residues that fall outside query columns become lowercase
insertions -- so no external MSA tool is required.

AF3's A3M requirements (docs/input.md), all enforced and verified here:
  1. A3M format: FASTA, lowercase = insertion, '-' = gap
  2. First sequence is exactly the query sequence
  3. With lowercase removed, every row is exactly len(query) characters

Usage:
    python build_casrx_msa.py \
        --csv "[Konermann 2023] Cas13d ortholog sequences.csv" \
        --out casrx_orthologs.a3m

Then inject into AF3 input JSONs with add_msa_to_json.py.
"""

import argparse
import sys
import pandas as pd
from Bio import Align
from Bio.Align import substitution_matrices


def build_aligner():
    aligner = Align.PairwiseAligner()
    aligner.mode = "global"
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.open_gap_score = -11.0
    aligner.extend_gap_score = -1.0
    # Free end gaps: orthologs range 877-1034aa vs the 967aa query, so
    # terminal length differences should not be penalised.
    try:
        aligner.end_gap_score = 0.0
    except AttributeError:
        aligner.target_end_gap_score = 0.0
        aligner.query_end_gap_score = 0.0
    return aligner


def to_a3m_row(q_aln: str, h_aln: str) -> str:
    """
    Convert a pairwise alignment into one A3M row, anchored on the query.

    For every query column (query has a residue): emit the homolog residue
    uppercase, or '-' if the homolog has a gap there.
    For every non-query column (query has a gap): emit the homolog residue
    lowercase -- an insertion relative to the query.

    Exactly one character is emitted per query residue, so stripping
    lowercase yields exactly len(query) characters.
    """
    row = []
    for qc, hc in zip(q_aln, h_aln):
        if qc != "-":
            row.append(hc.upper() if hc != "-" else "-")
        elif hc != "-":
            row.append(hc.lower())
    return "".join(row)


def pct_identity(query: str, a3m_row: str) -> float:
    """Identity over query columns (lowercase insertions excluded)."""
    cols = [c for c in a3m_row if not c.islower()]
    assert len(cols) == len(query)
    matches = sum(1 for q, c in zip(query, cols) if q == c)
    return 100.0 * matches / len(query)


def main():
    ap = argparse.ArgumentParser(description="Build a query-anchored A3M for CasRx")
    ap.add_argument("--csv", required=True, help="Cas13d ortholog sequences CSV")
    ap.add_argument("--out", default="casrx_orthologs.a3m", help="Output A3M path")
    ap.add_argument("--query_name", default="CasRx",
                    help="Name of the query row in the CSV (default: CasRx)")
    ap.add_argument("--min_identity", type=float, default=0.0,
                    help="Drop orthologs below this %% identity to the query")
    ap.add_argument("--expect_sequence", default=None,
                    help="Optional: assert the query sequence equals this exact string")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=["Sequence"])
    df["Sequence"] = df["Sequence"].astype(str).str.strip().str.upper()

    # -- query --------------------------------------------------------------
    qrows = df[df["Name"].astype(str).str.strip() == args.query_name]
    if len(qrows) != 1:
        sys.exit(f"ERROR: expected exactly 1 row named {args.query_name!r}, found {len(qrows)}")
    query = qrows["Sequence"].iloc[0]
    print(f"Query {args.query_name}: {len(query)} aa")

    if args.expect_sequence and query != args.expect_sequence.strip().upper():
        sys.exit("ERROR: query sequence does not match --expect_sequence. The A3M's "
                 "first sequence MUST exactly equal the 'sequence' field in the AF3 JSON.")

    homologs = df[df["Name"].astype(str).str.strip() != args.query_name]
    print(f"Orthologs to align: {len(homologs)}")

    # -- align --------------------------------------------------------------
    aligner = build_aligner()
    records = []
    for _, r in homologs.iterrows():
        name, seq = str(r["Name"]).strip(), r["Sequence"]
        try:
            aln = aligner.align(query, seq)[0]
        except Exception as e:
            print(f"  SKIP {name}: alignment failed ({e})")
            continue
        q_aln, h_aln = aln[0], aln[1]
        row = to_a3m_row(q_aln, h_aln)
        ident = pct_identity(query, row)
        if ident < args.min_identity:
            print(f"  drop {name}: {ident:.1f}% identity < {args.min_identity}%")
            continue
        records.append((name, row, ident))

    records.sort(key=lambda x: -x[2])

    # -- validate -----------------------------------------------------------
    print("\nValidating A3M constraints ...")
    bad = []
    for name, row, _ in records:
        stripped = "".join(c for c in row if not c.islower())
        if len(stripped) != len(query):
            bad.append((name, len(stripped)))
    if bad:
        for name, n in bad:
            print(f"  FAIL {name}: {n} match columns, expected {len(query)}")
        sys.exit("ERROR: A3M rows are not rectangular over query columns.")
    print(f"  OK: all {len(records)} rows have exactly {len(query)} match columns")

    # -- write --------------------------------------------------------------
    with open(args.out, "w") as f:
        f.write(f">{args.query_name}\n{query}\n")          # requirement 2
        for name, row, _ in records:
            safe = name.replace(" ", "_")
            f.write(f">{safe}\n{row}\n")

    print(f"\nWrote {args.out}")
    print(f"  depth: {len(records) + 1} sequences (query + {len(records)} orthologs)")
    idents = [i for _, _, i in records]
    if idents:
        print(f"  identity to query: max {max(idents):.1f}%  median "
              f"{sorted(idents)[len(idents)//2]:.1f}%  min {min(idents):.1f}%")
    print("\nTop 10 by identity:")
    for name, _, ident in records[:10]:
        print(f"  {name:<20} {ident:5.1f}%")


if __name__ == "__main__":
    main()
