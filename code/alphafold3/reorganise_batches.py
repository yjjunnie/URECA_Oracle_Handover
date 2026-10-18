#!/usr/bin/env python3
"""
reorganise_batches.py
=====================
Splits all 500 AF3 input JSONs into batches of 10 for efficient
PBS array job submission (50 jobs total instead of 500).

Each batch gets its own subdirectory under af3_inputs_batched/.
AF3 will use --input_dir to process all 10 JSONs in a batch
sequentially within one PBS job.

The MSA outputs (af3_outputs_msa/) stay flat, AF3 finds the
_data.json for each complex automatically since --output_dir
points to af3_outputs_msa/ and --force_output_dir is set.

Usage:
    python3 reorganise_batches.py

Creates:
    /scratch/users/ntu/<YOUR_NSCC_ID>/af3_inputs_batched/
        batch_00/   <- 10 JSONs (indices 0-9)
        batch_01/   <- 10 JSONs (indices 10-19)
        ...
        batch_49/   <- 10 JSONs (indices 490-499)
"""

import os
import shutil
import glob

# Paths
AF3_INPUT     = "/scratch/users/ntu/<YOUR_NSCC_ID>/af3_inputs"
BATCHED_INPUT = "/scratch/users/ntu/<YOUR_NSCC_ID>/af3_inputs_batched"
BATCH_SIZE    = 10

# Get sorted list of all JSONs
all_jsons = sorted(glob.glob(os.path.join(AF3_INPUT, "*.json")))
print(f"Total JSONs: {len(all_jsons)}")
print(f"Batch size:  {BATCH_SIZE}")
print(f"Batches:     {len(all_jsons) // BATCH_SIZE}")
print()

os.makedirs(BATCHED_INPUT, exist_ok=True)

for batch_num, i in enumerate(range(0, len(all_jsons), BATCH_SIZE)):
    chunk     = all_jsons[i:i + BATCH_SIZE]
    batch_dir = f"batch_{batch_num:02d}"
    in_dir    = os.path.join(BATCHED_INPUT, batch_dir)
    os.makedirs(in_dir, exist_ok=True)

    for json_path in chunk:
        shutil.copy2(json_path, os.path.join(in_dir, os.path.basename(json_path)))

    print(f"  batch_{batch_num:02d}: {len(chunk)} guides "
          f"({os.path.basename(chunk[0]).replace('.json','')} ... "
          f"{os.path.basename(chunk[-1]).replace('.json','')})")

print(f"\nDone, {batch_num+1} batches in {BATCHED_INPUT}/")
print("Ready to submit 03_af3_inference_batched.pbs")
