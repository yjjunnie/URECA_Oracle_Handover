# ProGen3 Repository Code Flow Guide

This is a **protein language model** repository implementing ProGen3, a transformer-based model for protein sequence generation and scoring.

## 🎯 High-Level Overview

ProGen3 is designed for two main tasks:
1. **Scoring**: Computing likelihood/perplexity of protein sequences
2. **Generation**: Creating new protein sequences (extending or infilling)

## 📁 Repository Structure

```
progen3-main/
├── src/progen3/              # Main package
│   ├── modeling.py           # Core transformer model
│   ├── config.py             # Model configuration
│   ├── tokenizer.py          # Tokenization utilities
│   ├── tokenizer.json        # Tokenizer vocab (file you have open)
│   ├── batch_preparer.py     # Data preprocessing
│   ├── scorer.py             # Scoring API
│   ├── generator.py          # Generation API
│   │
│   ├── model/                # Architecture components
│   │   ├── attention.py      # Multi-head attention + RoPE
│   │   ├── moe.py            # Mixture of Experts
│   │   └── mb_wrapper.py     # MegaBlocks MoE integration
│   │
│   ├── common/               # Utilities
│   │   ├── dist.py           # Distributed training
│   │   └── model_loading.py  # FSDP loading
│   │
│   └── tools/                # CLI applications
│       ├── score.py          # Scoring CLI
│       ├── generate.py       # Generation CLI
│       └── utils.py          # Shared utilities
│
└── examples/                 # Usage examples
```

## 🔄 Main Code Flows

### 1. **Scoring Flow** (Compute sequence likelihood)

```
FASTA File → Tokenizer → BatchPreparer → ProGen3Model → Scorer → CSV Output
```

**Step-by-step:**
1. Read protein sequences from FASTA file
2. Tokenize sequences (using tokenizer.json)
3. Prepare batches in both directions (N→C and C→N)
4. Run model inference bidirectionally
5. Compute negative log-likelihood
6. Average scores and output to CSV

**Entry points:**
- CLI: `src/progen3/tools/score.py`
- API: `src/progen3/scorer.py` (`ProGen3Scorer` class)

### 2. **Generation Flow** (Create new sequences)

```
Prompt CSV → BatchPreparer → ProGen3Model.generate() → Validator → FASTA Output
```

**Step-by-step:**
1. Read prompts from CSV (with min/max token lengths)
2. Detect mode: **CLM** (extension) or **GLM** (infilling)
3. Prefill KV-cache with prompt tokens
4. Sample tokens autoregressively
5. Validate and compile sequences
6. Output to FASTA files

**Entry points:**
- CLI: `src/progen3/tools/generate.py`
- API: `src/progen3/generator.py` (`ProGen3Generator` class)

### 3. **Model Architecture Flow**

```
Input Tokens
    ↓
Token Embeddings + Sequence Embeddings
    ↓
┌─────────────────────────────────────┐
│ DecoderLayer × N (repeated blocks)  │
│  ├─ RMSNorm                         │
│  ├─ Attention (with RoPE)           │
│  ├─ RMSNorm                         │
│  └─ MoE (Mixture of Experts)        │
│      └─ Router → Top-K Experts      │
└─────────────────────────────────────┘
    ↓
Final RMSNorm
    ↓
LM Head (project to vocabulary)
    ↓
Logits → Loss/Predictions
```

**Key components:**
- `src/progen3/modeling.py`: `ProGen3ForCausalLM` (main model), `DecoderLayer`
- `src/progen3/model/attention.py`: Multi-head attention with Rotary Position Embeddings
- `src/progen3/model/moe.py` or `src/progen3/model/mb_wrapper.py`: Sparse MoE layers

## 🔑 Key Files Explained

### Core Model Files

1. **`src/progen3/modeling.py`** (717 lines)
   - `ProGen3ForCausalLM`: Main model with generation capabilities
   - `ProGen3Model`: Base transformer with MoE layers
   - `DecoderLayer`: Single transformer block (attention + MoE)

2. **`src/progen3/config.py`** (165 lines)
   - `ProGen3Config`: All model hyperparameters
   - Controls: attention heads, MoE experts, quantization, etc.

3. **`src/progen3/batch_preparer.py`** (225 lines)
   - Converts protein sequences to model inputs
   - Supports **CLM** (standard generation) and **GLM** (infilling) modes
   - Handles bidirectional sequences (forward/reverse)

### Model Components

4. **`src/progen3/model/attention.py`** (250 lines)
   - Grouped-query attention (GQA)
   - Rotary Position Embeddings (RoPE)
   - Uses Flash Attention for efficiency

5. **`src/progen3/model/moe.py`** (142 lines)
   - Sparse Mixture of Experts implementation
   - Router selects top-k experts per token
   - Feed-forward networks (MLP/GLUMLP)

6. **`src/progen3/model/mb_wrapper.py`** (188 lines)
   - MegaBlocks integration for distributed MoE
   - Expert parallelism across GPUs

### High-Level APIs

7. **`src/progen3/scorer.py`** (183 lines)
   - `ProGen3Scorer.score_batch()`: Compute log-likelihood and perplexity
   - Automatic bidirectional scoring

8. **`src/progen3/generator.py`** (241 lines)
   - `ProGen3Generator.generate()`: Generate sequences
   - Supports extension and infilling
   - KV-cache optimization

## 🎨 Special Features

### Bidirectional Modeling
Sequences are processed in both directions:
- **Forward (N→C)**: Normal amino acid order
- **Reverse (C→N)**: Reversed order
- Scores are averaged for robustness

### Dual-Mode Generation
1. **CLM (Causal Language Model)**: Extend sequences
   - Example: `MALW...` → `MALW...KQRTV` (continuation)

2. **GLM (Generalized Language Model)**: Fill gaps
   - Example: `MALW[GLM]KQRTV` → `MALWXXXXXKQRTV` (infill middle)

### Mixture of Experts (MoE)
- Each token is routed to top-k experts (not all experts)
- Enables larger model capacity with sparse computation
- MegaBlocks library provides efficient distributed execution

## 💻 Usage Examples

### CLI Usage

**Scoring:**
```bash
torchrun -m progen3.tools.score \
  --fasta-path sequences.fasta \
  --model-name Profluent-Bio/progen3-3b
```

**Generation:**
```bash
torchrun -m progen3.tools.generate \
  --prompt-file prompts.csv \
  --output-dir outputs/
```

### Python API Usage

```python
import torch
from progen3.modeling import ProGen3ForCausalLM
from progen3.batch_preparer import ProGen3BatchPreparer
from progen3.scorer import ProGen3Scorer

# Load model
model = ProGen3ForCausalLM.from_pretrained(
    "Profluent-Bio/progen3-3b",
    torch_dtype=torch.bfloat16
).eval().cuda()

# Score sequences
scorer = ProGen3Scorer(model=model)
scores = scorer.score_batch(sequences=["MALWMRLL..."])
print(scores["log_likelihood"][0])

# Generate sequences
outputs = model.generate(input_ids=inputs["input_ids"])
```

## 🔍 Important Patterns

1. **Always bidirectional**: Sequences scored/generated in both directions
2. **Special tokens**: `<bos>`, `<eos>`, `<bos_glm>`, `<eos_span>`, direction markers (1/2)
3. **FSDP-ready**: Fully Sharded Data Parallel for multi-GPU training
4. **Flash Attention**: Triton kernels for fast, memory-efficient attention
5. **KV-cache**: Generation optimized by caching key/value states

## 🚀 Getting Started

1. **Explore examples**: Check `examples/` directory
2. **Read configs**: Understand model settings in `src/progen3/config.py`
3. **Try scoring**: Start with `src/progen3/tools/score.py` on sample FASTA
4. **Debug flow**: Add breakpoints in `src/progen3/batch_preparer.py` to see data transformations

## 📊 Detailed Architecture Overview

### Component Interaction Flow

```
User Input (FASTA/CSV)
         ↓
    Tokenizer (tokenizer.py)
         ↓
    BatchPreparer (batch_preparer.py)
         ↓
    [input_ids, position_ids, sequence_ids, labels]
         ↓
    ProGen3Model (modeling.py)
         ├→ Embedding Layer (token + sequence embeddings)
         ├→ DecoderLayers × N (num_hidden_layers)
         │    ├→ RMSNorm
         │    ├→ Attention (model/attention.py)
         │    │    └→ RotaryPositionalEmbedding
         │    ├→ RMSNorm
         │    └→ MoE (model/moe.py or mb_wrapper.py)
         │         ├→ Router (expert selection)
         │         └→ Experts (MLP/GLUMLP)
         └→ Final RMSNorm
         ↓
    ProGen3ForCausalLM
         └→ LM Head (hidden → vocab logits)
         ↓
    [logits, loss, aux_loss]
         ↓
    Scorer/Generator
         ↓
    Output (CSV/FASTA)
```

### External Dependencies

- **PyTorch** (≥2.5.0): Core deep learning framework
- **Transformers** (≥4.42, <4.49): HuggingFace model utilities
- **MegaBlocks**: Efficient sparse MoE implementation
- **Flash Attention**: Fast attention kernels (Triton)
- **BioPython**: FASTA file parsing
- **Click**: CLI framework
- **Pandas, SciPy**: Data processing and evaluation

## 🔬 Advanced Features

### Scoring Details

The scoring process in `src/progen3/scorer.py`:
1. Parse FASTA file (BioPython)
2. Batch sequences by length to maximize GPU utilization
3. Distribute batches across ranks (multi-GPU)
4. For each sequence:
   - Prepare forward direction (N→C)
   - Prepare reverse direction (C→N)
   - Run model inference on both directions
   - Compute negative log-likelihood (cross-entropy loss)
   - Average bidirectional scores
5. Gather scores from all ranks
6. Reorder by original sequence indices
7. Write CSV with `sequence_id`, `log_likelihood`, `perplexity`

### Generation Details

The generation process in `src/progen3/generator.py`:
1. Parse CSV: `id`, `sequence`, `min_new_tokens`, `max_new_tokens`
2. Detect mode (CLM vs GLM) via pattern matching
3. Parse direction (1=forward, 2=reverse)
4. Prepare input encoding with batch_preparer
5. Prefill KV-cache with prompt tokens (optimization)
6. Sample tokens autoregressively using model.generate():
   - Temperature and top-p sampling
   - Stop at `<eos>` (CLM) or `<eos_span>` (GLM)
7. Validate generated sequences (pattern matching)
8. Compile sequences:
   - CLM: Concatenate prompt + generation (handle direction)
   - GLM: Insert generation into specified span
9. Gather from all ranks
10. Output:
    - `{id}.gen.fasta`: Raw model outputs
    - `{id}.seq.fasta`: Validated protein sequences

The repository is well-structured with clear separation between model architecture (`modeling.py`), data handling (`batch_preparer.py`), and user-facing APIs (`scorer.py`, `generator.py`).
