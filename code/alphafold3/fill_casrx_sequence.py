"""
fill_casrx_sequence.py
======================
Fetches RfxCas13d (CasRx) protein sequence from UniProt A0A1C5SD84
and fills it into all AF3 input JSON files.

Designed to run inside a PBS job on NSCC — no login node interaction needed.
Uses only standard library (urllib) — no conda/pip installs required.

Usage:
    python fill_casrx_sequence.py --json_dir /scratch/users/ntu/<YOUR_NSCC_ID>/af3_inputs/

    # Or if UniProt is unreachable, supply a local FASTA:
    python fill_casrx_sequence.py --json_dir /scratch/users/ntu/<YOUR_NSCC_ID>/af3_inputs/ \
                                  --fasta_file /scratch/users/ntu/<YOUR_NSCC_ID>/casrx.fasta

RfxCas13d identity:
    - Full name: Ruminococcus flavefaciens XPD3002 Cas13d
    - Also known as: CasRx
    - UniProt: A0A1C5SD84
    - PDB: 6IV9 (binary complex with crRNA)
    - Used by: TIGER (Wessels et al. 2023 Nat Biotechnol), Konermann et al. 2018 Cell
    - Length: ~930 amino acids, starts with MAST
    - Direct repeat (DNA alphabet): AACCCCTACCAACTGGTCGGGGTTTGAAAC (30 nt)

Note on Addgene backbone:
    The RfxCas13d-backbone plasmid contains the DR sequence in its U6/guide
    expression cassette, confirming TIGER uses RfxCas13d. However the partial
    sequence on Addgene does not include the protein CDS — always fetch from UniProt.
"""

import argparse
import glob
import json
import os
import re
import sys
import urllib.request
import urllib.error


UNIPROT_ID  = "A0A1C5SD84"
UNIPROT_URL = f"https://www.uniprot.org/uniprot/{UNIPROT_ID}.fasta"
PLACEHOLDER = "CASRX_SEQUENCE_PLACEHOLDER"
EXPECTED_MIN_LEN = 900
EXPECTED_MAX_LEN = 980   # UniProt A0A1C5SD84 is 967 aa
EXPECTED_START   = "MAST"


def fetch_from_uniprot():
    print(f"Fetching CasRx from UniProt: {UNIPROT_URL}")
    try:
        req = urllib.request.Request(
            UNIPROT_URL,
            headers={"User-Agent": "Mozilla/5.0 (research)"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            fasta = r.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"ERROR fetching from UniProt: {e}")
        print("Options:")
        print("  1. Check compute node internet access on NSCC")
        print("  2. Download manually: wget https://www.uniprot.org/uniprot/A0A1C5SD84.fasta")
        print("     Then rerun with --fasta_file casrx.fasta")
        sys.exit(1)
    seq = "".join(l.strip() for l in fasta.split("\n") if not l.startswith(">"))
    return re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", seq.upper())


def load_from_fasta(path):
    print(f"Loading CasRx from local FASTA: {path}")
    with open(path) as f:
        lines = f.readlines()
    seq = "".join(l.strip() for l in lines if not l.startswith(">"))
    return re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", seq.upper())


def validate(seq):
    ok = True
    if not (EXPECTED_MIN_LEN <= len(seq) <= EXPECTED_MAX_LEN):
        print(f"WARNING: Length {len(seq)} aa — expected {EXPECTED_MIN_LEN}–{EXPECTED_MAX_LEN}")
        ok = False
    else:
        print(f"  Length: {len(seq)} aa ✓")

    if not seq.startswith(EXPECTED_START):
        print(f"WARNING: Starts with '{seq[:10]}' — expected '{EXPECTED_START}...'")
        ok = False
    else:
        print(f"  Starts: {seq[:20]} ✓")

    if not ok:
        ans = input("Sequence looks wrong. Continue anyway? [y/N]: ")
        if ans.strip().lower() != "y":
            sys.exit(1)


def fill_jsons(json_dir, seq):
    files = sorted(glob.glob(os.path.join(json_dir, "*.json")))
    if not files:
        print(f"ERROR: No JSON files found in {json_dir}")
        sys.exit(1)

    print(f"\nProcessing {len(files)} JSON files...")
    filled = already = errors = 0

    for fpath in files:
        try:
            with open(fpath) as f:
                job = json.load(f)
            modified = False
            for chain in job.get("sequences", []):
                if "protein" in chain:
                    curr = chain["protein"].get("sequence", "")
                    if curr == PLACEHOLDER:
                        chain["protein"]["sequence"] = seq
                        modified = True
                    elif curr.startswith("MAST"):
                        already += 1
            if modified:
                with open(fpath, "w") as f:
                    json.dump(job, f, indent=2)
                filled += 1
        except Exception as e:
            print(f"  ERROR: {os.path.basename(fpath)}: {e}")
            errors += 1

    print(f"  Filled:   {filled}")
    print(f"  Skipped (already filled): {already}")
    if errors:
        print(f"  Errors:   {errors}")
    return filled


def verify(json_dir, seq):
    files = sorted(glob.glob(os.path.join(json_dir, "*.json")))
    if not files:
        return
    with open(files[0]) as f:
        job = json.load(f)
    for chain in job.get("sequences", []):
        if "protein" in chain:
            actual = chain["protein"].get("sequence", "")
            if actual == seq:
                print(f"\nVerified {os.path.basename(files[0])}: protein = {len(actual)} aa ✓")
            elif actual == PLACEHOLDER:
                print("ERROR: Placeholder still present after fill — something went wrong")
                sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_dir",   required=True, help="Directory with AF3 JSON inputs")
    parser.add_argument("--fasta_file", default=None,  help="Local FASTA (optional, skips UniProt fetch)")
    args = parser.parse_args()

    seq = load_from_fasta(args.fasta_file) if args.fasta_file else fetch_from_uniprot()

    print("\nValidating sequence:")
    validate(seq)

    filled = fill_jsons(args.json_dir, seq)
    if filled > 0:
        verify(args.json_dir, seq)
        print(f"\nDone — {filled} files updated.")
    else:
        print("\nNo files needed updating.")


if __name__ == "__main__":
    main()
