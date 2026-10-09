# ProGen3 Scorer Input/Output Examples

## Quick Overview

The ProGen3 scorer takes protein sequences as input and outputs:
1. **Log-likelihood**: A score indicating how natural/probable the sequence is
2. **Perplexity**: Another measure of sequence quality (lower is better)

## Example 1: Simple Python Usage

### Input (Python)
```python
from progen3.modeling import ProGen3ForCausalLM
from progen3.scorer import ProGen3Scorer
import torch

model = ProGen3ForCausalLM.from_pretrained("Profluent-Bio/progen3-3b", torch_dtype=torch.bfloat16)
model = model.eval().to("cuda:0")

scorer = ProGen3Scorer(model=model)

# Input: a list of protein sequences (amino acid strings)
sequences = [
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
    "MKFLKFSLLTAVLLSVVFAFSSCGDDDDTISNSESDKRHCDFAYKKFLHQSHDNKKDEEEHLKLAGLTGRTYTVFQLKRKRPPHELPANLIEKYHNNKQP"
]

scores = scorer.score_batch(sequences=sequences)
```

### Output (Python)
```python
scores = {
    'log_likelihood': [-45.2341, -52.8976],  # Higher (less negative) is better
    'perplexity': [1.234e10, 2.567e11]       # Lower is better
}

# Access individual scores:
print(scores["log_likelihood"][0])  # -45.2341
print(scores["perplexity"][1])      # 2.567e11
```

## Example 2: CLI Usage with FASTA File

### Input File (`sequences.fasta`)
```
>seq_id_1
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN
>seq_id_2
MKFLKFSLLTAVLLSVVFAFSSCGDDDDTISNSESDKRHCDFAYKKFLHQSHDNKKDEEEHLKLAGLTGRTYTVFQLKRKRPPHELPANLIEKYHNNKQP
>seq_id_3
MTEITAAMVKELRESTGAGMMDCKNALSETNGDFDKAVQLLREKGLGKAAKKADRLAAEG
```

### Command
```bash
torchrun --nproc-per-node=gpu -m progen3.tools.score \
  --fasta-path sequences.fasta \
  --output-path scores.csv \
  --model-name Profluent-Bio/progen3-3b \
  --fsdp
```

### Output File (`scores.csv`)
```csv
sequence_id,log_likelihood,perplexity
seq_id_1,-45.234123,12345678901.234
seq_id_2,-52.897654,256789012345.678
seq_id_3,-38.123456,5678901234.567
```

## Example 3: Real Use Case - Comparing Wild-type vs Mutant

### Input
```python
sequences = [
    # Wild-type sequence
    "MTEITAAMVKELRESTGAGMMDCKNALSETNGDFDKAVQLLREKGLGKAAKKADRLAAEG",
    # Mutant with beneficial mutation
    "MTEITAAMVKELRESTGAGMMDCKNALSETNGDFDKAVQLLREKGLGKAAKKADRLAAED",
    # Mutant with deleterious mutation (introduced stop codon-like disruption)
    "MTEITAAMVKELRESTGAGMMDXXXALSETNGDFDKAVQLLREKGLGKAAKKADRLAAEG"
]

scores = scorer.score_batch(sequences=sequences)
```

### Expected Output Pattern
```python
{
    'log_likelihood': [
        -38.1234,  # Wild-type (baseline)
        -38.5678,  # Beneficial mutant (slightly lower, still natural)
        -67.8901   # Deleterious mutant (much lower, unnatural)
    ],
    'perplexity': [
        5.678e9,   # Wild-type
        6.234e9,   # Beneficial mutant
        8.901e12   # Deleterious mutant (much higher, worse)
    ]
}
```

## How to Interpret the Scores

### Log-likelihood
- **Range**: Typically very negative (e.g., -30 to -200)
- **Higher is better**: -30 is better than -100
- **Meaning**: Probability of the sequence under the model
  - More natural sequences have higher (less negative) scores
  - Unusual/unnatural sequences have lower (more negative) scores

### Perplexity
- **Range**: Positive numbers, can be very large
- **Lower is better**: 1000 is better than 1,000,000
- **Meaning**: exp(-log_likelihood)
  - Lower perplexity = model is more confident (better sequence)
  - Higher perplexity = model is less confident (unusual sequence)

## Typical Workflows

### 1. Ranking Designed Sequences
```python
# Score 100 designed protein variants
scores = scorer.score_batch(designed_sequences)

# Sort by log-likelihood (best first)
ranked = sorted(zip(designed_sequences, scores['log_likelihood']),
                key=lambda x: x[1], reverse=True)

# Select top 10 for experimental validation
top_10 = ranked[:10]
```

### 2. Mutation Effect Prediction
```python
# Score wild-type and mutants
wt_score = scorer.score_batch([wild_type])['log_likelihood'][0]
mutant_scores = scorer.score_batch(mutants)['log_likelihood']

# Calculate effect (higher = more favorable)
effects = [mut_score - wt_score for mut_score in mutant_scores]
```

## Running the Demo

You can run the demo script to see actual output:

```bash
python demo_scorer.py
```

This will show you:
- Exactly what the input sequences look like
- The scoring process
- Actual numerical outputs
- How to interpret the results
