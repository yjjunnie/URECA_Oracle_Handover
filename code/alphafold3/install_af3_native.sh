#!/bin/bash
# ============================================================
# install_af3_native.sh
# Native (container-free) AlphaFold 3 install for NSCC.
#
# Why native instead of the Singularity image:
#   * The official Singularity route requires `docker build` first, then a
#     local Docker registry -- both need root, which we don't have.
#   * Roughly half the AF3 Dockerfile is building HMMER from source. HMMER is
#     used ONLY by the data pipeline (jackhmmer/nhmmer MSA search). We supply
#     our own MSA, so we skip HMMER entirely.
#   * The ~600GB genetic databases are likewise unused with
#     --norun_data_pipeline, so they are not installed here.
#
# Fixes the two toolchain problems on the NSCC login node:
#   * system gcc is 8.5.0 (2021) -- too old for libcifpp/dssp C++17/20.
#     conda-forge compilers give us gcc 12+ with no root needed.
#   * system cmake is 3.26.5, but pyproject requires >=3.28. Not an issue:
#     pip's build isolation fetches its own cmake+ninja wheels.
#
# Run on a COMPUTE node if login-node CPU limits bite -- the C++ build
# (libcifpp + dssp) is the slow part. No GPU needed to build.
#
# Usage:  bash install_af3_native.sh
# ============================================================
set -euo pipefail

ENV_NAME="af3"
SRC_DIR="/scratch/users/ntu/<YOUR_NSCC_ID>/alphafold3_src"

echo "=== AlphaFold 3 native install ==="
echo "Start: $(date)"

# ── conda ────────────────────────────────────────────────────
source "$(conda info --base)/etc/profile.d/conda.sh"

if conda env list | grep -qE "^${ENV_NAME}\s"; then
    echo "Conda env '${ENV_NAME}' already exists, reusing it."
else
    echo "Creating conda env '${ENV_NAME}' (python 3.12) ..."
    conda create -y -n "${ENV_NAME}" python=3.12
fi
conda activate "${ENV_NAME}"
echo "Python: $(python --version)"

# ── modern toolchain (the whole point: system gcc 8.5 is too old) ──
echo ""
echo "Installing conda-forge compilers ..."
conda install -y -c conda-forge gcc_linux-64 gxx_linux-64 zlib zstd

# conda-forge compiler activation scripts export CC/CXX. Re-activate so they
# take effect in this shell, then confirm we actually got a modern gcc.
conda deactivate && conda activate "${ENV_NAME}"
echo "CC  = ${CC:-unset}"
echo "CXX = ${CXX:-unset}"
GCC_MAJOR=$("${CXX:-g++}" -dumpversion | cut -d. -f1)
echo "g++ version: $("${CXX:-g++}" -dumpversion)"
if [ "${GCC_MAJOR}" -lt 11 ]; then
    echo "ERROR: compiler is still too old (need >= 11). CXX=${CXX:-unset}"
    exit 1
fi

# ── source ───────────────────────────────────────────────────
echo ""
if [ -d "${SRC_DIR}/.git" ]; then
    echo "Source already present at ${SRC_DIR}"
else
    echo "Cloning AlphaFold 3 source (code is public; only the weights are gated) ..."
    git clone https://github.com/google-deepmind/alphafold3.git "${SRC_DIR}"
fi
cd "${SRC_DIR}"

# ── build + install ──────────────────────────────────────────
# Build isolation supplies scikit_build_core, pybind11, cmake>=3.28, ninja.
# This compiles the C++ extensions and fetches libcifpp/dssp -- the slow step.
echo ""
echo "Building and installing alphafold3 (this compiles C++; expect 10-30 min) ..."
pip install --upgrade pip
pip install .

# ── chemical component database ──────────────────────────────
echo ""
echo "Running build_data (chemical components database) ..."
build_data

# ── verify ───────────────────────────────────────────────────
echo ""
echo "=== verification ==="
python -c "
import alphafold3, jax
print('alphafold3 imported OK')
print('jax', jax.__version__)
print('devices:', jax.devices())
"

echo ""
echo "Done: $(date)"
echo ""
echo "NOTE: jax.devices() will show CPU on a login node: that is expected."
echo "      Check for GPU from a GPU compute node before running inference."
echo ""
echo "To use in a PBS job:"
echo "  source \$(conda info --base)/etc/profile.d/conda.sh"
echo "  conda activate ${ENV_NAME}"
echo "  export XLA_FLAGS='--xla_gpu_enable_triton_gemm=false'"
echo "  export XLA_PYTHON_CLIENT_PREALLOCATE=true"
echo "  export XLA_CLIENT_MEM_FRACTION=0.95"
echo "  python ${SRC_DIR}/run_alphafold.py --json_path=... --model_dir=... \\"
echo "         --norun_data_pipeline --resolve_msa_overlaps=false"
