# AF3 curated-MSA validation: one complex

The single complex folded with the curated CasRx MSA, rather than AF3's own empty one. It
is the only evidence that the fix described in
[`../../../README.md` §2.3](../../../README.md#23-the-alphafold3-arm-is-invalid) works.

Complex: `casrx_TFRC_crRNA0565_1526_1548_PM`, a TFRC-targeting guide.
Produced by `code/alphafold3/03c_af3_inference_native.pbs` with the MSA injected by
`add_msa_to_json.py` from `code/alphafold3/casrx_orthologs.a3m`.

## What it shows

| Metric | Void 500-run (AF3 automatic MSA) | This run (curated MSA) |
|---|---|---|
| `ptm` | 0.19 | **0.85** |
| `chain_ptm`, protein chain A | 0.18 | **0.89** |
| Mean pLDDT | ~30 | **74.9** |
| `chain_ptm`, crRNA chain B | n/a | 0.15 |
| `chain_ptm`, target RNA chain C | n/a | 0.05 |
| `iptm` | n/a | 0.35 |

Read directly from `..._summary_confidences.json`, which holds
`chain_ptm: [0.89, 0.15, 0.05]`.

Two conclusions, and they pull in opposite directions:

1. **The protein folds correctly once it has an MSA.** 0.18 to 0.89 on chain A is the fix
   working, and it means the 500-run was measuring nothing.
2. **The RNA chains remain poorly modelled regardless**, at 0.15 and 0.05. This is why the
   project's overall negative conclusion is not expected to flip on a re-run, since the
   hypothesis is tested through interface quality. Expected, not demonstrated.

## Files

| File | Purpose |
|---|---|
| `..._summary_confidences.json` | The per-chain and whole-structure confidence scores. The numbers in the table above. |
| `..._model.cif` | The predicted structure, for inspection against PDB `9M31` / `9LZT`. |
| `..._data.json` | The input AF3 received, with the injected MSA in place. Use it as the worked example of what a correct input looks like. |

**Omitted:** `..._confidences.json`, the per-atom PAE and pLDDT arrays, at 9.2 MB. Re-derive
it by re-running the complex if per-residue detail is needed.

## What this is not

One complex, one seed. It is a validation that the pipeline now folds the protein, **not a
result**. The re-run across all 500 is task 1.0 in
[`../../../docs/05_next_steps.md`](../../../docs/05_next_steps.md) and has never been done.
