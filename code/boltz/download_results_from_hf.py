#!/usr/bin/env python3
"""
Download Boltz-2 analysis results from HuggingFace onto Windows.

Pulls everything under results_fullprot/ and results_balanced/ in the
HF dataset repo and lands them next to each other locally:
  results_fullprot/  -> boltz/correlation_results/
  results_balanced/  -> boltz/correlation_results_balanced/

Requires:
  pip install huggingface_hub

Run:
  python download_results_from_hf.py
"""

import os
from huggingface_hub import HfApi, hf_hub_download

# ── CONFIG ────────────────────────────────────────────────────────────────────
HF_TOKEN = os.environ["HF_TOKEN"]  # was hardcoded; read from env instead
HF_REPO  = "yjjunnie/ureca-boltz-data"
BASE     = r"c:\Users\holly\Documents\Documents\URECA_Code\boltz"
# ──────────────────────────────────────────────────────────────────────────────

DEST_DIRS = {
    "results_fullprot": os.path.join(BASE, "correlation_results"),
    "results_balanced":  os.path.join(BASE, "correlation_results_balanced"),
}

api = HfApi(token=HF_TOKEN)
all_files = api.list_repo_files(repo_id=HF_REPO, repo_type="dataset")

for prefix, dest_dir in DEST_DIRS.items():
    os.makedirs(dest_dir, exist_ok=True)
    matches = [f for f in all_files if f.startswith(prefix + "/")]
    if not matches:
        print(f"WARNING: no files found under {prefix}/ in the repo — skipping")
        continue

    print(f"\nDownloading {len(matches)} file(s) from {prefix}/ -> {dest_dir}")
    for repo_path in matches:
        fname = os.path.basename(repo_path)
        local_path = os.path.join(dest_dir, fname)
        print(f"  {repo_path} -> {local_path}")
        downloaded = hf_hub_download(
            repo_id=HF_REPO,
            filename=repo_path,
            repo_type="dataset",
            token=HF_TOKEN,
            local_dir=dest_dir,
            local_dir_use_symlinks=False,
        )
        # hf_hub_download may nest under the repo's own subfolder; flatten it
        if os.path.abspath(downloaded) != os.path.abspath(local_path):
            os.replace(downloaded, local_path)

print("\nAll results downloaded.")
