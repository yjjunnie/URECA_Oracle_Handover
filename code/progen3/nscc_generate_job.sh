#!/bin/bash
#PBS -N progen3_gen
#PBS -l select=1:ncpus=8:mem=64gb:ngpus=1
#PBS -l walltime=8:00:00
#PBS -j oe
#PBS -o generate.log

# ProGen3 Generation Job for NSCC (PBS)
# This script generates protein sequences using ProGen3

echo "========================================="
echo "ProGen3 Generation Job"
echo "Job ID: $PBS_JOBID"
echo "Node: $PBS_O_HOST"
echo "Start time: $(date)"
echo "========================================="

# Change to submission directory
cd $PBS_O_WORKDIR

# Load required modules
module purge
module load cuda/11.8
module load anaconda3

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

# Input prompt file (CSV format with columns: id, sequence, min_new_tokens, max_new_tokens)
PROMPT_FILE="prompts.csv"

# Output directory for generated sequences
OUTPUT_DIR="generation_outputs"

# Model to use
MODEL_NAME="Profluent-Bio/progen3-3b"

# Number of sequences to generate per prompt
N_PER_PROMPT=100

# Generation parameters
TEMPERATURE=0.85  # Higher = more diverse (0.8-1.0 typical)
TOP_P=0.95       # Nucleus sampling (0.9-0.95 typical)

# Number of GPUs
NUM_GPUS=1

# ========================================
# RUN GENERATION
# ========================================

echo "Configuration:"
echo "  Prompt file: $PROMPT_FILE"
echo "  Output directory: $OUTPUT_DIR"
echo "  Model: $MODEL_NAME"
echo "  Sequences per prompt: $N_PER_PROMPT"
echo "  Temperature: $TEMPERATURE"
echo "  Top-p: $TOP_P"
echo "  GPUs: $NUM_GPUS"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: Prompt file not found: $PROMPT_FILE"
    echo ""
    echo "Please create a CSV file with columns:"
    echo "  id,sequence,min_new_tokens,max_new_tokens"
    echo ""
    echo "Example:"
    echo "  prompt_1,1MKFL,50,100"
    echo "  prompt_2,2LKFM,100,200"
    echo ""
    exit 1
fi

# Run generation
echo "Starting generation..."
torchrun --nproc-per-node=$NUM_GPUS -m progen3.tools.generate \
    --prompt-file "$PROMPT_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --model-name "$MODEL_NAME" \
    --n-per-prompt $N_PER_PROMPT \
    --fsdp \
    --temperature $TEMPERATURE \
    --top-p $TOP_P

# Check if generation was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "Generation completed successfully!"
    echo "========================================="
    echo "Outputs saved to: $OUTPUT_DIR"
    echo ""
    echo "Generated files:"
    ls -lh "$OUTPUT_DIR"
    echo ""
    echo "File types:"
    echo "  *.gen.fasta - Raw generated tokens"
    echo "  *.seq.fasta - Valid protein sequences (prompt + generation)"
else
    echo ""
    echo "========================================="
    echo "ERROR: Generation failed!"
    echo "========================================="
    echo "Check the error log: generate.log"
    exit 1
fi

echo ""
echo "End time: $(date)"
echo "Job duration: $SECONDS seconds"
