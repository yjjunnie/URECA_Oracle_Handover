# data

Input data small enough to commit. Everything else is external; see
[`../docs/03_datasets.md`](../docs/03_datasets.md) for the full dataset inventory and
[`../docs/06_script_legend.md` §9.4](../docs/06_script_legend.md#94-datasets) for how to
obtain the rest.

| File | Size | Purpose |
|---|---|---|
| `konermann_2023_cas13d_ortholog_sequences.csv` | 51 KB | The 52 Cas13d ortholog protein sequences from Konermann 2023. |

## Why this one file is here

It is the input to two things, and without it neither can be run from this repository
alone:

1. **`code/alphafold3/build_casrx_msa.py`**, which builds the curated MSA from it. The
   generated MSA is committed as `code/alphafold3/casrx_orthologs.a3m`, so the alignment
   can be used directly, but this file is what lets it be rebuilt or extended.
2. **The unrun ProGen3 experiment**, task 1.2 in
   [`../docs/05_next_steps.md`](../docs/05_next_steps.md). Scoring these 52 orthologs is
   the whole experiment, and it is entirely set up apart from being pointed at this file.

Original filename in the working tree:
`[Konermann 2023] Cas13d ortholog sequences.csv`. Renamed here because the brackets and
spaces are awkward to pass on a command line.

## Not here

Datasets too large to commit, or not redistributable. The TIGER screens supply the activity
labels and the thermodynamic feature columns that every correlation in this project is
computed against, so obtaining them is the first data task, not an optional one.
