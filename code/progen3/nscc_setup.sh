#!/bin/bash
#PBS -N progen3_setup
#PBS -l select=1:ncpus=4:mem=32gb:ngpus=1
#PBS -l walltime=2:00:00
#PBS -j oe
#PBS -o setup.log

# ProGen3 Setup Script for NSCC (PBS)
# This script sets up the environment and installs ProGen3

echo "========================================="
echo "ProGen3 Setup on NSCC"
echo "Job ID: $PBS_JOBID"
echo "Node: $PBS_O_HOST"
echo "========================================="

# Change to submission directory
cd $PBS_O_WORKDIR

# Load required modules
echo "Loading modules..."
module purge
module load gcc/11.2.0-nscc
module load cuda/12.2.2

# Verify modules loaded correctly
echo "GCC version:"
gcc --version | head -1
echo "CUDA_HOME: $CUDA_HOME"
which nvcc

# Create conda environment
echo "Creating conda environment..."
ENV_NAME=progen3_env

# Check if environment already exists
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Environment $ENV_NAME already exists. Removing and recreating..."
    conda env remove -n $ENV_NAME -y
fi

echo "Creating new environment $ENV_NAME..."
conda create -n $ENV_NAME python=3.10 -y
source activate $ENV_NAME

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install PyTorch with CUDA 12.1 support (compatible with CUDA 12.2)
echo "Installing PyTorch with CUDA 12.1 support..."
pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify PyTorch CUDA compatibility
echo "Verifying PyTorch installation..."
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"

# Install ProGen3 and dependencies
echo "Installing ProGen3..."
pip install -e .

# Install megablocks (without [gg] to avoid grouped GEMM dependencies)
echo "Installing megablocks..."
pip install megablocks==0.7.0 --no-build-isolation

# Install flash-attention using prebuilt wheel (compilation often fails on NSCC)
echo "Installing flash-attention from prebuilt wheel..."
pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.5cxx11abiFALSE-cp310-cp310-linux_x86_64.whl

# Install other useful packages
echo "Installing additional packages..."
pip install biopython pandas scipy tqdm

# Install grouped GEMM (requires GPU)
echo "Installing grouped GEMM..."
pip install git+https://github.com/tgale96/grouped_gemm@main

# Verify installation
echo "========================================="
echo "Verifying installation..."
echo "========================================="

python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA version: {torch.version.cuda}')"
python -c "from progen3.modeling import ProGen3ForCausalLM; print('ProGen3 import successful!')"

echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "To use this environment in future jobs, add these lines to your job script:"
echo "  module load cuda/11.8"
echo "  module load anaconda3"
echo "  source activate $ENV_NAME"
echo ""
echo "You can now submit scoring or generation jobs."
