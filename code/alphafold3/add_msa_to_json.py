#!/usr/bin/env python3
"""
add_msa_to_json.py
==================
Injects a custom protein MSA (A3M) into AF3 input JSONs, and fills the
CasRx protein sequence at the same time.

Both are done here on purpose: AF3 requires the first sequence of the A3M
to be *exactly* the chain's `sequence` field, so setting them from a single
source in one pass removes the possibility of them drifting apart. This
replaces the need for a separate fill_casrx_sequence.py step (and its
UniProt fetch) for these inputs.

Per docs/input.md, supplying a custom MSA means setting, on the protein chain:
    unpairedMsa : the A3M string
    pairedMsa   : ""          (must be explicitly empty when unpairedMsa is set)
    templates   : []          (template-free)

RNA chains are left alone -- the generator already sets their unpairedMsa /
pairedMsa to "", which is the intended configuration for them.

The A3M is embedded inline rather than referenced via unpairedMsaPath. At
~56KB per JSON that is ~30MB across a 533-job run, which is negligible on
scratch, and it avoids every class of relative-path/bind-mount bug that a
path reference would expose inside the Singularity container.

IMPORTANT -- two changes to how you run AF3 after this:
  1. The MSA/data-pipeline step (02_af3_msa.pbs) is no longer needed for
     these inputs. AF3 will not build an MSA when one is supplied.
  2. Inference must add:  --resolve_msa_overlaps=false
     Without it, AF3 deduplicates the unpaired MSA against the paired MSA
     and can disturb the supplied alignment (docs/input.md, "MSA Pairing").

Usage:
    python add_msa_to_json.py --json_dir af3_inputs/af3_inputs_flowcyt \
                              --a3m casrx_orthologs.a3m
"""

import argparse
import glob
import json
import os
import sys


def read_a3m(path):
    """Return (a3m_text, query_sequence, n_records)."""
    with open(path) as f:
        text = f.read()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    names = [l for l in lines if l.startswith(">")]
    seqs = [l for l in lines if not l.startswith(">")]
    if not seqs:
        sys.exit(f"ERROR: no sequences found in {path}")
    query = seqs[0]
    if "-" in query or any(c.islower() for c in query):
        sys.exit("ERROR: the first A3M record (the query) must be ungapped and all uppercase.")
    # Verify rectangularity over query columns.
    for name, s in zip(names[1:], seqs[1:]):
        stripped = "".join(c for c in s if not c.islower())
        if len(stripped) != len(query):
            sys.exit(f"ERROR: {name} has {len(stripped)} match columns, expected {len(query)}")
    return text, query, len(seqs)


def main():
    ap = argparse.ArgumentParser(description="Inject a custom A3M MSA into AF3 input JSONs")
    ap.add_argument("--json_dir", required=True, help="Directory of AF3 input JSONs")
    ap.add_argument("--a3m", required=True, help="A3M file from build_casrx_msa.py")
    ap.add_argument("--protein_chain", default="A", help="Chain id of the protein (default: A)")
    ap.add_argument("--dry_run", action="store_true", help="Report without writing")
    args = ap.parse_args()

    a3m_text, query, depth = read_a3m(args.a3m)
    print(f"A3M: {args.a3m}")
    print(f"  depth: {depth} sequences | query: {len(query)} aa | {len(a3m_text)} bytes")

    files = sorted(glob.glob(os.path.join(args.json_dir, "*.json")))
    if not files:
        sys.exit(f"ERROR: no JSONs found in {args.json_dir}")
    print(f"\nJSONs found: {len(files)}")

    n_updated = 0
    n_seq_filled = 0
    problems = []

    for path in files:
        with open(path) as f:
            d = json.load(f)

        prot = None
        for chain in d.get("sequences", []):
            if "protein" in chain:
                ids = chain["protein"].get("id", [])
                ids = [ids] if isinstance(ids, str) else ids
                if args.protein_chain in ids:
                    prot = chain["protein"]
                    break
        if prot is None:
            problems.append((os.path.basename(path), f"no protein chain {args.protein_chain}"))
            continue

        existing = prot.get("sequence", "")
        if existing != query:
            # Placeholder, or a stale/differing sequence -- overwrite so the
            # chain sequence and the A3M query are guaranteed identical.
            prot["sequence"] = query
            n_seq_filled += 1

        prot["unpairedMsa"] = a3m_text
        prot["pairedMsa"] = ""
        prot["templates"] = []

        if not args.dry_run:
            with open(path, "w") as f:
                json.dump(d, f, indent=2)
        n_updated += 1

    print(f"\n{'(dry run) ' if args.dry_run else ''}Updated {n_updated} JSONs")
    print(f"  protein sequence written/corrected in: {n_seq_filled}")
    if problems:
        print(f"  PROBLEMS ({len(problems)}):")
        for name, msg in problems[:10]:
            print(f"    {name}: {msg}")

    print("\nReminders for the run:")
    print("  * Skip 02_af3_msa.pbs -- AF3 will not build an MSA when one is supplied.")
    print("  * Add --resolve_msa_overlaps=false to the inference command.")
    print("  * Verify on 1-2 jobs before submitting the full array.")


if __name__ == "__main__":
    main()
