# 02: Writing Your Own Job Scripts on NSCC

All GPU work ran on **NSCC ASPIRE** under **PBS Pro**. This is the most reusable part of
the handover: the science changes, the cluster mechanics do not.

Replace `hzhang08` / `ntu` with your own username and institution throughout.

---

## 1. Access

```powershell
ssh your_username@aspire2.nscc.sg      # aspire.nscc.sg also appears in older scripts
```

Windows needs OpenSSH Client: Settings → Apps → Optional Features → Add "OpenSSH Client".
Verify with `ssh -V`.

Transferring files from Windows:

```powershell
scp -O -r boltz your_username@aspire2.nscc.sg:/scratch/users/ntu/your_username/
```

**Use `-O`.** Without the legacy-protocol flag, large transfers to ASPIRE fail or stall.
This was a real time sink. For multi-GB weights, `scp -O` each file individually so a
failure does not restart the whole set.

---

## 2. The filesystem rule that matters most

```
/home/users/ntu/<user>/      small quota, code and scripts only
/scratch/users/ntu/<user>/   large quota, everything else; PURGED PERIODICALLY
```

Two consequences that caused most of the project's failures:

**(a) Redirect every cache to scratch.** Default temp dirs live under `/var/tmp` or
`$HOME` and will blow their quota mid-job, usually during `pip install` or Triton
kernel compilation. Every job script must set:

```bash
export TMPDIR="$SCRATCH/tmp"
export PIP_CACHE_DIR="$SCRATCH/pip_cache"
export TRITON_CACHE_DIR="$SCRATCH/triton_cache"     # PyTorch/Triton JIT
export TORCH_HOME="$SCRATCH/torch_hub"              # torch.hub checkpoints
export HF_HOME="$SCRATCH/hf_cache"                  # Hugging Face models
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$TRITON_CACHE_DIR" "$TORCH_HOME" "$HF_HOME"
```

**(b) Scratch is purged.** Results must be pushed off-cluster as the final pipeline stage,
not "later". The Boltz pipeline does this with
`upload_to_hf.py` + `05_upload_results.pbs` (Hugging Face as the result store) and
`download_results_from_hf.py` to pull them back to Windows. Reuse that pattern.

---

## 3. Anatomy of a PBS script

```bash
#!/bin/bash
#PBS -N my_job                                    # job name (appears in qstat)
#PBS -l select=1:ncpus=8:mem=64gb:ngpus=1         # ONE resource line, comma-free
#PBS -l walltime=06:00:00                         # hard kill at this time
#PBS -o /scratch/users/ntu/hzhang08/logs/my.out   # stdout
#PBS -e /scratch/users/ntu/hzhang08/logs/my.err   # stderr
#PBS -j oe                                        # (alternative) merge stderr into stdout
```

Rules learned the hard way:

- **`#PBS` lines must come before any executable line**: but comments are fine, so a
  header block of `#` documentation above them is allowed (see `boltz/03_boltz_batch.pbs`,
  which puts its usage notes first).
- **`mkdir -p` your log directory before submitting.** If `-o`'s directory does not exist
  the job dies silently with no output at all. This is the single most confusing failure
  mode on PBS.
- **Ask for the GPU explicitly** with `ngpus=1`. A job without it runs on a CPU node and
  `torch.cuda.is_available()` returns False, which looks like a broken install.
- Keep walltime honest. Short walltime = faster scheduling; overrunning = total loss of
  the job, so pad by ~2×.
- `cd $PBS_O_WORKDIR` to start in the submission directory (PBS otherwise starts in `$HOME`).

### Submitting and monitoring

```bash
qsub my_job.pbs              # submit, prints the job ID
qstat -u $USER               # your jobs
qstat -f <jobid>             # full detail, incl. why it is queued
qstat -J <jobid>             # array job summary
qdel <jobid>                 # cancel
cat /scratch/users/ntu/hzhang08/logs/my.out
```

---

## 4. Environments

Two approaches were used; both work.

**venv + module (used for Boltz, AF3, ESMFold).** Lighter, more reproducible:

```bash
module purge
module load python/3.11.7-gcc11
module load cuda/12.8.1

ENV_PATH="$SCRATCH/envs/myenv"
[ -d "$ENV_PATH" ] || python3 -m venv "$ENV_PATH"
source "$ENV_PATH/bin/activate"
```

**conda (used for ProGen3).** See `progen3-main/nscc_setup.sh`:

```bash
module purge
module load gcc/11.2.0-nscc
module load cuda/12.2.2
conda create -n progen3_env python=3.10 -y
source activate progen3_env     # NOT `conda activate` in a batch job
```

Modules seen in working scripts: `python/3.11.7-gcc11`, `cuda/12.8.1`, `cuda/12.2.2`,
`cuda/12.1`, `gcc/11.2.0-nscc`, `singularity/4.3.1`. Run `module avail`: these change.

**Build the environment in its own CPU-only job**, not inside your GPU job. Installs take
30+ minutes and burn GPU allocation doing nothing. `boltz/00_install_boltz.pbs` is the
pattern: no `ngpus`, just install and verify. Make it **idempotent** (`[ -d "$ENV_PATH" ] ||
...`) so a resubmit is free.

Use **separate envs for GPU inference and CPU analysis.** `05_analyze.pbs` uses
`$SCRATCH/envs/analysis` (pandas/scipy/seaborn only) so analysis jobs queue instantly on
CPU nodes instead of waiting for a GPU.

### The CUDA mismatch

The most common hard failure: `pip install` pulls a torch wheel built for a different CUDA
than the node has. Symptom: `torch.cuda.is_available()` is False despite `ngpus=1` and a
working `nvidia-smi`.

Always test before batching. `boltz/01_test_boltz.pbs` does exactly this:

```bash
nvidia-smi
python - << 'PYCHECK'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("torch cuda:", torch.version.cuda)
    print("gpu:", torch.cuda.get_device_name(0))
PYCHECK
```

If False, reinstall torch against the CUDA version `nvidia-smi` reports: that is all
`boltz/02_fix_torch_cuda.pbs` does.

### Containers

AF3 ran under Singularity (`module load singularity/4.3.1`) from `alphafold3.sif`. Bind
scratch paths in explicitly; the container cannot see them otherwise. Also set a JAX
compilation cache (`$SCRATCH/jax_cache`) or every task recompiles from scratch.

---

## 5. Array jobs: the right way to run N complexes

Never submit N separate jobs. Use a PBS array: one script, many indices.

```bash
#PBS -J 0-64            # 65 tasks, indices 0..64
#PBS -J 0-49%10         # 50 tasks, at most 10 running concurrently
#PBS -o /scratch/users/ntu/hzhang08/logs/      # directory, note trailing slash
```

Inside the script, `$PBS_ARRAY_INDEX` identifies the task. The pattern used throughout
this project is **manifest + offset**: write one TSV listing every work item, then have
each task slice its own rows.

```bash
TASK_ID=${PBS_ARRAY_INDEX}
BATCH_SIZE=20
# task 0 -> rows 0-19, task 1 -> rows 20-39, ...
```

Three details that make this robust, all taken from `boltz/03_boltz_batch.pbs`:

1. **Copy the task's inputs into a private directory** (`$SCRATCH/tmp/batch_input_$TASK_ID`)
   before running. Pointing many concurrent tasks at one shared input directory causes
   them to process each other's files.
2. **Exit 0 cleanly when the slice is empty.** The last task usually has fewer rows than
   `BATCH_SIZE`; an overrun should not look like a failure.
3. **Compute the array range from the data, not by hand.** `generate_yamls.py` prints the
   correct `#PBS -J 0-N` line as its last output; paste it in. Hardcoding a stale range
   silently skips work.

With `-o` set to a directory, array logs land as
`<jobid>[<index>].pbs101.OU` / `.ER`, quote those paths in the shell, the brackets are
glob characters.

```bash
cat "/scratch/users/ntu/hzhang08/logs/123456[3].pbs101.OU"
```

---

## 6. Recommended pipeline shape

Numbered, single-purpose scripts, each resumable. This is what all three pipelines
converged on, and it is worth copying:

```
00_install_*.pbs     CPU   build env, verify inputs exist, idempotent
01_test_*.pbs        GPU   smoke test ONE item end to end; print output schema
02_fix_*.pbs         GPU   remediation for the known CUDA failure
generate_inputs.py   login build inputs + manifest; print the array range
03_batch_*.pbs       GPU   array job over the manifest
04_analyze.py, pure analysis, no cluster assumptions
05_analyze.pbs       CPU   thin wrapper that runs 04 in the analysis env
06_upload_*.pbs      CPU   push results off scratch before it is purged
```

Two habits that paid off repeatedly:

- **Stage 01 must print the output schema**, not just "it worked". `01_test_boltz.pbs`
  `cat`s the confidence JSON specifically so the exact key names are known *before* the
  parser in `04_analyze.py` is written. Guessing key names then re-running 1,300 GPU jobs
  is the expensive mistake this avoids.
- **Put a usage comment block at the top of every script**: what it needs, what it
  produces, what to submit next. Every script in `boltz/` does this, and it is why the
  pipeline is still readable months later.

---

## 7. Templates

Copy-paste starting points in [`../templates/`](../templates/):

| File | Use |
|---|---|
| `single_gpu.pbs` | one GPU task; includes the cache redirects and the CUDA check |
| `array_job.pbs` | manifest-driven array job with private input dirs |
| `cpu_analysis.pbs` | CPU-only analysis job |
| `boltz_input.yaml` | Boltz-2 Cas13d complex input |

---

## 8. Failure checklist

| Symptom | Cause |
|---|---|
| No output file at all | `-o`/`-e` directory does not exist, `mkdir -p` it |
| `torch.cuda.is_available()` False | missing `ngpus=1`, or torch/CUDA mismatch |
| Quota error during `pip install` | `TMPDIR`/`PIP_CACHE_DIR` not redirected to scratch |
| Quota error mid-inference | `TRITON_CACHE_DIR` not redirected |
| Job killed with no error | walltime exceeded |
| Array tasks process wrong files | shared input dir, give each task a private one |
| Results gone | scratch purged; upload at the end of the pipeline |
| Container cannot find files | scratch paths not bound into Singularity |
| `conda activate` fails in a job | use `source activate` |
| Large `scp` to ASPIRE stalls | missing `-O` |
