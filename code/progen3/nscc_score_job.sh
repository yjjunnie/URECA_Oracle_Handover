#!/bin/bash
#PBS -N progen3_score
#PBS -l select=1:ncpus=8:mem=64gb:ngpus=1
#PBS -l walltime=4:00:00
#PBS -j oe
#PBS -o score.log

# ProGen3 Scoring Job for NSCC (PBS)
# This script scores protein sequences using ProGen3

echo "========================================="
echo "ProGen3 Scoring Job"
echo "Job ID: $PBS_JOBID"
echo "Node: $PBS_O_HOST"
echo "Start time: $(date)"
echo "========================================="

# Change to submission directory
cd $PBS_O_WORKDIR

# Load required modules
module purge
module load cuda/12.2.2

# Activate conda environment
source activate progen3_env

# Check GPU availability
echo "Checking GPU..."
nvidia-smi

# Navigate to project directory (if not already in submission directory)
# cd ~/progen3-main  # Uncomment and adjust path if needed

# ========================================
# CONFIGURATION - EDIT THESE PARAMETERS
# ========================================

# Input FASTA file (sequences to score)
FASTA_PATH="my_sequences.fasta"

# Output CSV file (where scores will be saved)
OUTPUT_PATH="scores.csv"

# Model to use (choose based on GPU memory):
# - Profluent-Bio/progen3-112m (smallest, ~4GB VRAM)
# - Profluent-Bio/progen3-219m (~8GB VRAM)
# - Profluent-Bio/progen3-339m (~12GB VRAM)
# - Profluent-Bio/progen3-762m (~20GB VRAM)
# - Profluent-Bio/progen3-1b   (~30GB VRAM)
# - Profluent-Bio/progen3-3b   (~40GB VRAM, requires A100)
MODEL_NAME="Profluent-Bio/progen3-3b"

# Number of GPUs to use (should match ngpus above)
NUM_GPUS=1

# ========================================
# RUN SCORING
# ========================================

echo "Configuration:"
echo "  Input FASTA: $FASTA_PATH"
echo "  Output CSV: $OUTPUT_PATH"
echo "  Model: $MODEL_NAME"
echo "  GPUs: $NUM_GPUS"
echo ""

# Check if input file exists
if [ ! -f "$FASTA_PATH" ]; then
    echo "ERROR: Input FASTA file not found: $FASTA_PATH"
    echo "Please create the file or update FASTA_PATH in this script."
    exit 1
fi

# Run scoring using patched scorer (with grouped_gemm disabled)
echo "Starting scoring..."
torchrun --nproc-per-node=$NUM_GPUS score_no_grouped_gemm.py \
    --fasta-path "$FASTA_PATH" \
    --output-path "$OUTPUT_PATH" \
    --model-name "$MODEL_NAME"

# Check if scoring was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "Scoring completed successfully!"
    echo "========================================="
    echo "Output saved to: $OUTPUT_PATH"
    echo ""
    echo "Preview of results:"
    head -n 10 "$OUTPUT_PATH"
    echo ""
    echo "Total sequences scored: $(($(wc -l < "$OUTPUT_PATH") - 1))"
else
    echo ""
    echo "========================================="
    echo "ERROR: Scoring failed!"
    echo "========================================="
    echo "Check the error log: score.log"
    exit 1
fi

echo ""
echo "End time: $(date)"
echo "Job duration: $SECONDS seconds"
