#!/usr/bin/env python3
"""
Download Boltz-2 data + scripts from HuggingFace onto NSCC.

Copy this file to NSCC and run:
  module load python/3.11.7-gcc11
  source /scratch/users/ntu/<YOUR_NSCC_ID>/envs/boltz/bin/activate
  python download_from_hf.py

Or paste the two lines below directly in the NSCC terminal
(replace token and repo with your own).
"""

import os
from huggingface_hub import hf_hub_download

# ── CONFIG ────────────────────────────────────────────────────────────────────
HF_TOKEN = os.environ["HF_TOKEN"]  # was hardcoded; read from env instead
HF_REPO  = "yjjunnie/ureca-boltz-data"
SCRATCH  = "/scratch/users/ntu/<YOUR_NSCC_ID>"
# ──────────────────────────────────────────────────────────────────────────────

REPO_FILES = [
    ("data/flow-cytometry.bz2",   f"{SCRATCH}/data/flow-cytometry.bz2"),
    ("data/hap-titration.bz2",    f"{SCRATCH}/data/hap-titration.bz2"),
    ("data/konermann_seqs.xlsx",  f"{SCRATCH}/data/konermann_seqs.xlsx"),
    ("data/konermann_kd.xlsx",    f"{SCRATCH}/data/konermann_kd.xlsx"),
    ("data/azimuth_V1.xlsx",      f"{SCRATCH}/data/azimuth_V1.xlsx"),
    ("scripts/generate_yamls.py",  f"{SCRATCH}/generate_yamls.py"),
    ("scripts/generate_yamls.pbs", f"{SCRATCH}/generate_yamls.pbs"),
    ("scripts/03_boltz_batch.pbs",       f"{SCRATCH}/03_boltz_batch.pbs"),
    ("scripts/04_analyze.py",            f"{SCRATCH}/04_analyze.py"),
    ("scripts/04b_analyze_balanced.py",  f"{SCRATCH}/04b_analyze_balanced.py"),
    ("scripts/05_analyze.pbs",           f"{SCRATCH}/05_analyze.pbs"),
    ("scripts/05b_analyze_balanced.pbs", f"{SCRATCH}/05b_analyze_balanced.pbs"),
]

for repo_path, dest_path in REPO_FILES:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    print(f"Downloading {repo_path} …", flush=True)
    local = hf_hub_download(
        repo_id=HF_REPO,
        filename=repo_path,
        repo_type="dataset",
        token=HF_TOKEN,
        local_dir=os.path.dirname(dest_path),
        local_dir_use_symlinks=False,
    )
    # hf_hub_download may put the file in a subdirectory; rename to dest_path
    if os.path.abspath(local) != os.path.abspath(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        os.replace(local, dest_path)
    print(f"  → {dest_path}", flush=True)

print("\nAll files downloaded. Next:")
print("  python /scratch/users/ntu/<YOUR_NSCC_ID>/generate_yamls.py")
