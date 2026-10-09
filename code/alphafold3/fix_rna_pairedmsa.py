#!/usr/bin/env python3
"""
fix_rna_pairedmsa.py
Removes the invalid 'pairedMsa' key from RNA chains in AF3 input JSONs.

AF3's RnaChain.from_dict accepts only:
    id, sequence, modifications, description, unpairedMsa, unpairedMsaPath
'pairedMsa' is protein-only (MSA pairing is a protein-multimer concept), so
its presence on an RNA chain raises:
    ValueError: Unexpected JSON keys in: pairedMsa
Older AF3 builds tolerated the extra key; current ones validate strictly.

'unpairedMsa': '' is kept -- for RNA that means "run MSA-free for this chain",
which is what we want with --norun_data_pipeline.

Usage: python fix_rna_pairedmsa.py <json_dir>
"""
import glob, json, os, sys

d = sys.argv[1] if len(sys.argv) > 1 else "."
files = sorted(glob.glob(os.path.join(d, "*.json")))
if not files:
    sys.exit(f"No JSONs found in {d}")

fixed = clean = 0
for p in files:
    with open(p) as f:
        j = json.load(f)
    changed = False
    for chain in j.get("sequences", []):
        if "rna" in chain and "pairedMsa" in chain["rna"]:
            del chain["rna"]["pairedMsa"]
            changed = True
    if changed:
        with open(p, "w") as f:
            json.dump(j, f, indent=2)
        fixed += 1
    else:
        clean += 1

print(f"scanned {len(files)} JSONs: {fixed} fixed, {clean} already clean")

# verify
bad = []
for p in files:
    with open(p) as f:
        j = json.load(f)
    for chain in j.get("sequences", []):
        if "rna" in chain and "pairedMsa" in chain["rna"]:
            bad.append(os.path.basename(p))
print("remaining with pairedMsa on RNA:", len(bad))
