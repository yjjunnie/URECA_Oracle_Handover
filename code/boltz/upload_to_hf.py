#!/usr/bin/env python3
"""
Upload Boltz-2 data + scripts to a private HuggingFace dataset repo.

Run once from Windows:
  python upload_to_hf.py

Requires:
  pip install huggingface_hub

Your HF token:
  https://huggingface.co/settings/tokens  (needs write permission)
"""

import os
from huggingface_hub import HfApi, create_repo

# ── CONFIG: edit these two lines ─────────────────────────────────────────────
HF_TOKEN  = os.environ["HF_TOKEN"]  # was hardcoded; read from env instead
HF_REPO   = "yjjunnie/ureca-boltz-data"
# ──────────────────────────────────────────────────────────────────────────────

BASE = r"<PATH_TO_PROJECT>"

FILES = {
    # local path  →  path inside HF repo
    os.path.join(BASE, "tiger-main", "tiger_full", "data-processed", "flow-cytometry.bz2"):
        "data/flow-cytometry.bz2",
    os.path.join(BASE, "tiger-main", "tiger_full", "data-processed", "hap-titration.bz2"):
        "data/hap-titration.bz2",
    os.path.join(BASE, "[Konermann 2023] Individual guide sequences.xlsx"):
        "data/konermann_seqs.xlsx",
    os.path.join(BASE, "[Konermann 2023] Raw data for individual guide knockdown efficiency and survival rate.xlsx"):
        "data/konermann_kd.xlsx",
    os.path.join(BASE, "Azimuth-master", "azimuth", "data", "V1_data.xlsx"):
        "data/azimuth_V1.xlsx",
    os.path.join(BASE, "boltz", "generate_yamls.py"):
        "scripts/generate_yamls.py",
    os.path.join(BASE, "boltz", "generate_yamls.pbs"):
        "scripts/generate_yamls.pbs",
    os.path.join(BASE, "boltz", "03_boltz_batch.pbs"):
        "scripts/03_boltz_batch.pbs",
    os.path.join(BASE, "boltz", "04_analyze.py"):
        "scripts/04_analyze.py",
    os.path.join(BASE, "boltz", "04b_analyze_balanced.py"):
        "scripts/04b_analyze_balanced.py",
    os.path.join(BASE, "boltz", "05_analyze.pbs"):
        "scripts/05_analyze.pbs",
    os.path.join(BASE, "boltz", "05b_analyze_balanced.pbs"):
        "scripts/05b_analyze_balanced.pbs",
}

api = HfApi(token=HF_TOKEN)

# Create repo if it doesn't exist yet
try:
    create_repo(HF_REPO, repo_type="dataset", private=True, token=HF_TOKEN)
    print(f"Created private dataset repo: {HF_REPO}")
except Exception as e:
    if "already exists" in str(e).lower() or "409" in str(e):
        print(f"Repo already exists: {HF_REPO}")
    else:
        raise

# Upload each file
for local_path, repo_path in FILES.items():
    if not os.path.exists(local_path):
        print(f"  SKIP (not found): {local_path}")
        continue
    size_kb = os.path.getsize(local_path) / 1024
    print(f"  Uploading {os.path.basename(local_path)} ({size_kb:.0f} KB) → {repo_path}")
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=repo_path,
        repo_id=HF_REPO,
        repo_type="dataset",
        token=HF_TOKEN,
    )

print("\nDone. On NSCC run:")
print(f'  python download_from_hf.py  (or paste the commands from that script)')
