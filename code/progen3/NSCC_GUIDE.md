# ProGen3 on NSCC - Complete Guide

Quick guide to run ProGen3 protein scorer on NSCC's GPU clusters using PBS.

## Prerequisites

- NSCC account with GPU allocation
- ~20GB storage quota
- Windows 10/11 with OpenSSH Client installed

**Check if OpenSSH is installed:**
```powershell
ssh -V
```

If not installed: Settings → Apps → Optional Features → Add "OpenSSH Client"

---

## Setup Steps

### 1. Connect to NSCC

```powershell
ssh <YOUR_NSCC_ID>@aspire.nscc.sg
```

### 2. Upload Code to NSCC

**Option A: Upload from Windows (PowerShell)**
```powershell
cd "<PATH_TO_PROJECT>\Documents\Documents"
scp -r progen3-main <YOUR_NSCC_ID>@aspire.nscc.sg:~/
```

**Option B: Clone from GitHub (recommended)**
```bash
# On NSCC
cd ~
git clone https://github.com/profluent-ai/progen3.git progen3-main
cd progen3-main
```

### 3. Create Job Scripts

If you cloned from GitHub, create the NSCC job scripts:

```bash
# On NSCC
cd ~/progen3-main

# Create setup script
cat > nscc_setup.sh << 'EOF'
#!/bin/bash
#PBS -N progen3_setup
#PBS -l select=1:ncpus=4:mem=32gb:ngpus=1
#PBS -l walltime=2:00:00
#PBS -j oe
#PBS -o setup.log

echo "========================================="
echo "ProGen3 Setup on NSCC"
echo "Job ID: $PBS_JOBID"
echo "========================================="

cd $PBS_O_WORKDIR

# Load required modules
module purge
module load gcc/11.2.0-nscc
module load cuda/12.2.2

ENV_NAME=progen3_env
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "Removing existing environment..."
    conda env remove -n $ENV_NAME -y
fi

conda create -n $ENV_NAME python=3.10 -y
source activate $ENV_NAME

pip install --upgrade pip

# Install PyTorch with CUDA 12.1 (compatible with CUDA 12.2)
pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

pip install -e .
pip install megablocks==0.7.0 --no-build-isolation
MAX_JOBS=4 pip install flash-attn==2.7.4.post1 --no-build-isolation
pip install biopython pandas scipy tqdm

echo "Setup complete!"
EOF

# Create scoring script
cat > nscc_score_job.sh << 'EOF'
#!/bin/bash
#PBS -N progen3_score
#PBS -l select=1:ncpus=8:mem=64gb:ngpus=1
#PBS -l walltime=4:00:00
#PBS -j oe
#PBS -o score.log

echo "========================================="
echo "ProGen3 Scoring Job"
echo "Job ID: $PBS_JOBID"
echo "========================================="

cd $PBS_O_WORKDIR

# Load CUDA module
module purge
module load cuda/12.2.2

source activate progen3_env

nvidia-smi

FASTA_PATH="my_sequences.fasta"
OUTPUT_PATH="scores.csv"
MODEL_NAME="Profluent-Bio/progen3-3b"
NUM_GPUS=1

if [ ! -f "$FASTA_PATH" ]; then
    echo "ERROR: Input file not found: $FASTA_PATH"
    exit 1
fi

torchrun --nproc-per-node=$NUM_GPUS -m progen3.tools.score \
    --fasta-path "$FASTA_PATH" \
    --output-path "$OUTPUT_PATH" \
    --model-name "$MODEL_NAME" \
    --fsdp

if [ $? -eq 0 ]; then
    echo "Scoring completed successfully!"
    head -n 10 "$OUTPUT_PATH"
else
    echo "ERROR: Scoring failed!"
    exit 1
fi
EOF

# Make executable
chmod +x nscc_setup.sh nscc_score_job.sh
```

### 4. First-Time Setup (Run Once)

```bash
qsub nscc_setup.sh
```

Monitor setup (~30-60 minutes):
```bash
qstat -u <YOUR_NSCC_ID>
tail -f setup.log
```

### 5. Prepare Input Sequences

**Option A: Create on NSCC**
```bash
nano my_sequences.fasta
```

Example format:
```
>seq_1
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN
>seq_2
MKFLKFSLLTAVLLSVVFAFSSCGDDDDTISNSESDKRHCDFAYKKFLHQSHDNKKDEEEHLKLAGLTGRTYTVFQLKRKRPPHELPANLIEKYHNNKQP
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`

**Option B: Upload from Windows**
```powershell
scp my_sequences.fasta <YOUR_NSCC_ID>@aspire.nscc.sg:~/progen3-main/
```

### 6. Configure Scoring Job

```bash
nano nscc_score_job.sh
```

Edit these lines:
```bash
FASTA_PATH="my_sequences.fasta"
OUTPUT_PATH="scores.csv"
MODEL_NAME="Profluent-Bio/progen3-3b"  # See model options below
```

**Model Options:**
| Model | GPU RAM | Best For |
|-------|---------|----------|
| progen3-112m | ~4GB | Testing |
| progen3-762m | ~20GB | Production |
| progen3-1b | ~30GB | Production |
| progen3-3b | ~40GB | Best accuracy (A100) |

### 7. Submit Job

```bash
qsub nscc_score_job.sh
```

### 8. Monitor Job

```bash
# Check status
qstat -u <YOUR_NSCC_ID>

# Watch log
tail -f score.log
```

**Job States:**
- `Q` = Queued (waiting)
- `R` = Running
- `F` = Finished

### 9. Download Results

**View on NSCC:**
```bash
cat scores.csv
```

**Download to Windows:**
```powershell
# From PowerShell on Windows
scp <YOUR_NSCC_ID>@aspire.nscc.sg:~/progen3-main/scores.csv .
```

**Output Format:**
```csv
sequence_id,log_likelihood,perplexity
seq_1,-45.234,1.23e10
seq_2,-52.897,2.56e11
```

- **log_likelihood**: Higher (less negative) = better sequence
- **perplexity**: Lower = better sequence

---

## PBS Commands Reference

```bash
# Submit job
qsub nscc_score_job.sh

# Check status
qstat -u <YOUR_NSCC_ID>

# Job details
qstat -f <job_id>

# Cancel job
qdel <job_id>

# View log
tail -f score.log

# Interactive session
qsub -I -l select=1:ncpus=8:mem=64gb:ngpus=1 -l walltime=2:00:00
```

---

## PowerShell File Transfer Commands

```powershell
# Upload single file
scp my_file.fasta <YOUR_NSCC_ID>@aspire.nscc.sg:~/progen3-main/

# Upload directory
scp -r progen3-main <YOUR_NSCC_ID>@aspire.nscc.sg:~/

# Download single file
scp <YOUR_NSCC_ID>@aspire.nscc.sg:~/progen3-main/scores.csv .

# Download directory
scp -r <YOUR_NSCC_ID>@aspire.nscc.sg:~/progen3-main/results .
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Out of memory | Use smaller model: `MODEL_NAME="Profluent-Bio/progen3-1b"` |
| CUDA not available | Check `#PBS -l select=1:ncpus=8:mem=64gb:ngpus=1` in job script |
| Job pending long time | Try smaller model or check queue: `qstat -Q` |
| Module not found | Check available: `module avail` and update script |
| scp not found | Install OpenSSH: Settings → Apps → Optional Features |

---

## Job Script Configuration

Edit `nscc_score_job.sh` to customize:

```bash
# Resources (PBS header)
#PBS -l select=1:ncpus=8:mem=64gb:ngpus=1  # CPU, RAM, GPU
#PBS -l walltime=4:00:00                    # Max runtime

# Input/Output
FASTA_PATH="my_sequences.fasta"
OUTPUT_PATH="scores.csv"

# Model
MODEL_NAME="Profluent-Bio/progen3-3b"
NUM_GPUS=1
```

---

## NSCC Storage Locations

- **Home** (`~`): Limited space, for code and scripts
- **Scratch** (`/scratch/users/<username>`): Large temporary storage for data

---

## Support

- **NSCC Help**: help@nscc.sg | https://help.nscc.sg
- **ProGen3 Issues**: https://github.com/profluent-ai/progen3/issues
