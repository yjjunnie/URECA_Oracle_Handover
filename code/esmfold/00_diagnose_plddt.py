#!/usr/bin/env python3
"""
00_diagnose_plddt.py
====================
Establish whether the ESMFold pipeline is producing correct pLDDT before any
Cas13 experiment is run.

Folds reference proteins with KNOWN expected ESMFold confidence and prints
every candidate pLDDT aggregation side by side:

  A. out["mean_plddt"]          -- the correct, atom-masked value
  B. out["plddt"].mean()        -- the naive mean the esmfold.py docstring
                                   suggests; averages over all 37 atom slots
                                   including ones that do not exist
  C. CA-only per-residue mean   -- what a PDB B-factor column shows
  D. B-factor mean from PDB     -- what you get parsing output_to_pdb()

Expected if the pipeline is HEALTHY:
    ubiquitin / GB1  -> A around 85-95   (well-folded, abundant in training)
    alpha-synuclein  -> A around 25-40   (genuinely disordered - TRUE low score)

Interpretation:
  * ubiquitin A ~90 and synuclein A ~30 -> pipeline is fine; the "30" came from
    reading statistic B/C/D instead of A, or from batch padding.
  * ubiquitin A ~30 as well              -> pipeline is broken (weights not
    loaded, truncation, or dtype issue). Nothing downstream is meaningful.

Each sequence is folded twice: alone, and inside a mixed-length batch. A gap
between those two exposes padding contamination in the aggregation.

Run:
  python 00_diagnose_plddt.py
"""

import os
import sys
import numpy as np
import torch

# ── Reference sequences with known behaviour ──────────────────────────────────
# The first two are small, abundant, unambiguously folded domains: ESMFold is
# expected to be highly confident. The third is a bona fide intrinsically
# disordered protein and SHOULD score low - it is the control that proves a low
# score can still be a real signal rather than a bug.
REFERENCES = {
    "ubiquitin": (
        "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
    ),
    "GB1_domain": (
        "MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE"
    ),
    "alpha_synuclein_IDP": (
        "MDVFMKGLSKAKEGVVAAAEKTKQGVAEAAGKTKEGVLYVGSKTKEGVVHGVATVAEKTKEQVTNVGGAVVTGVTAVAQ"
        "KTVEGAGSIAAATGFVKKDQLGKNEEGAPQEGILEDMPVDPDNEAYEMPSEEGYQDYEPEA"
    ),
}

EXPECTED = {
    "ubiquitin":           "85-95  (folded)",
    "GB1_domain":          "85-95  (folded)",
    "alpha_synuclein_IDP": "25-40  (disordered - low is CORRECT)",
}


# ── Aggregation variants ──────────────────────────────────────────────────────
def all_statistics(out, index):
    """Every plausible way someone might have summarised pLDDT, for one item."""
    plddt = out["plddt"][index]                 # [L, 37], 0-100 scale
    exists = out["atom37_atom_exists"][index]   # [L, 37], 1 where atom is real

    # A: correct - mask to real atoms only
    a = (plddt * exists).sum() / exists.sum()

    # B: the docstring trap - averages the ~29 nonexistent atom slots per
    #    residue straight into the mean
    b = plddt.mean()

    # C: CA atom only (atom37 index 1); the usual per-residue readout
    ca_mask = exists[:, 1] > 0
    c = plddt[ca_mask, 1].mean()

    return float(a), float(b), float(c)


def bfactor_mean_from_pdb(pdb_str):
    """Mean of the B-factor column, i.e. what a PDB parser would report."""
    vals = [
        float(line[60:66])
        for line in pdb_str.splitlines()
        if line.startswith(("ATOM", "HETATM"))
    ]
    return float(np.mean(vals)) if vals else float("nan")


# ── Load model ────────────────────────────────────────────────────────────────
print("Loading ESMFold v1 …", flush=True)
import esm

model = esm.pretrained.esmfold_v1()
model = model.eval()

# Confirm the checkpoint actually loaded. A randomly initialised trunk is a
# silent failure mode that yields uniformly meaningless confidence.
n_params = sum(p.numel() for p in model.parameters())
w = model.trunk.blocks[0].seq_attention.proj.weight if hasattr(model, "trunk") else None
print(f"  parameters: {n_params/1e9:.2f}B")
if w is not None:
    print(f"  sample weight norm: {float(w.norm()):.4f}  (a near-0 or ~1.0 "
          f"value on a fresh init is suspicious)")

if torch.cuda.is_available():
    model = model.cuda()
    print(f"  device: cuda ({torch.cuda.get_device_name(0)})")
else:
    print("  device: CPU - this will be slow but works for these short refs")

model.set_chunk_size(128)


# ── Pass 1: fold each reference ALONE ─────────────────────────────────────────
print("\n" + "=" * 78)
print("PASS 1 - each sequence folded alone (no padding possible)")
print("=" * 78)
print(f"{'sequence':<24}{'len':>5}{'A:mean_plddt':>14}{'B:naive':>10}"
      f"{'C:CA':>9}{'D:bfac':>9}   expected (A)")
print("-" * 78)

alone = {}
for name, seq in REFERENCES.items():
    with torch.no_grad():
        out = model.infer([seq])
    a, b, c = all_statistics(out, 0)
    d = bfactor_mean_from_pdb(model.output_to_pdb(out)[0])
    alone[name] = a
    print(f"{name:<24}{len(seq):>5}{a:>14.1f}{b:>10.1f}{c:>9.1f}{d:>9.1f}   "
          f"{EXPECTED[name]}")


# ── Pass 2: fold all of them together as one padded batch ─────────────────────
print("\n" + "=" * 78)
print("PASS 2 - same sequences in one mixed-length batch (padding present)")
print("=" * 78)
print(f"{'sequence':<24}{'A:mean_plddt':>14}{'B:naive':>10}{'C:CA':>9}"
      f"{'drift vs alone (A)':>22}")
print("-" * 78)

names = list(REFERENCES)
with torch.no_grad():
    out = model.infer([REFERENCES[n] for n in names])

for i, name in enumerate(names):
    a, b, c = all_statistics(out, i)
    drift = a - alone[name]
    print(f"{name:<24}{a:>14.1f}{b:>10.1f}{c:>9.1f}{drift:>+22.2f}")


# ── Verdict ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("VERDICT")
print("=" * 78)

ubi = alone["ubiquitin"]
syn = alone["alpha_synuclein_IDP"]

if ubi < 50:
    print(f"  BROKEN. Ubiquitin scored {ubi:.1f} via the correct statistic (A).")
    print("  A 76-residue domain this abundant must land 85-95. The checkpoint,")
    print("  the dtype, or the input encoding is wrong. Do not interpret any")
    print("  Cas13 number until this reads ~90.")
elif syn > 70:
    print(f"  SUSPECT. Disordered alpha-synuclein scored {syn:.1f}, which is far")
    print("  too high. The confidence head is not discriminating.")
else:
    print(f"  Pipeline is HEALTHY: ubiquitin {ubi:.1f}, disordered control {syn:.1f}.")
    print("  Compare columns above against whatever your teammate reported. If")
    print("  their 30 matches column B, C or D rather than A, the bug is in the")
    print("  aggregation, not the model - re-derive every score using")
    print('  out["mean_plddt"], then re-run the Cas13 set.')
print()
