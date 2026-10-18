# Complete Guide: Reimplementing TIGER for Your Own Use Case

This guide explains what you need to modify to adapt the TIGER (Target Inference by Genetic Essentiality Response) project for your own machine learning use case.

---

## Table of Contents
1. [Data Structure & File Format](#1-data-structure--file-format)
2. [Sequence Encoding](#2-sequence-encoding)
3. [Labeling & Filtering](#3-labeling--filtering)
4. [Model Architecture](#4-model-architecture)
5. [Train/Validation Splitting](#5-trainvalidation-splitting)
6. [Calibration & Scoring](#6-calibration--scoring)
7. [Performance Metrics](#7-performance-metrics)
8. [Hardware & Dependencies](#8-hardware--dependencies)
9. [Hyperparameters to Tune](#9-hyperparameters-to-tune)
10. [File Paths & Organization](#10-file-paths--organization)
11. [Common Pitfalls & Solutions](#11-common-pitfalls--solutions)
12. [Minimal Example](#12-minimal-example-for-your-use-case)
13. [Critical Decision Checklist](#13-critical-decision-checklist)
14. [Recommended Implementation Order](#14-recommended-reimplementation-order)

---

## 1. Data Structure & File Format

### Input Data Files (`data.py:80-84`)

**Current setup:**
- Expects compressed pickle files: `data-processed/{dataset}.bz2`
- File contains pandas DataFrame with specific columns

**What you need to change:**
```python
# Instead of:
data_file = os.path.join('data-processed', dataset + '.bz2')
data = pd.read_pickle(data_file)

# Make it flexible:
def load_data(data_path, file_format='csv'):
    if file_format == 'csv':
        data = pd.read_csv(data_path)
    elif file_format == 'pickle':
        data = pd.read_pickle(data_path)
    elif file_format == 'parquet':
        data = pd.read_parquet(data_path)
    # ... map your columns to expected names
    return data
```

### Required Columns

**CRISPR-specific columns you need to adapt:**

| TIGER Column | Purpose | Your Equivalent? |
|--------------|---------|------------------|
| `gene` | Target gene name | Sample ID, protein, patient, etc. |
| `guide_id` | Unique guide identifier | Treatment ID, compound ID |
| `guide_seq` | Guide RNA sequence (variable length) | Your intervention sequence/descriptor |
| `target_seq` | DNA target (fixed ~23bp) | Your target sequence (if applicable) |
| `5p_context`, `3p_context` | Genomic context sequences | Flanking regions (if applicable) |
| `guide_type` | PM/SM/DM/RDM/TM/RTM | Perturbation category |
| `lfc_r1`, `lfc_r2`, `lfc_r3` | Replicate measurements | Your outcome replicates |
| `observed_lfc` | Mean of replicates | Your aggregated outcome |
| `observed_label` | Binary active/inactive | Your classification label |
| `fold` | Train/validation split | Your cross-validation strategy |

**Additional CRISPR-specific features** (`data.py:16-57`):
- Location features: `loc_utr_5p`, `loc_cds`, `loc_utr_3p`, `log_gene_len`
- Junction features: `junction_olap_5p`, `junction_dist_5p`
- Structure features: `direct_repeat`, `g_quad`, `mfe`
- Accessibility features: `log_unpaired_11`, etc.

**Decision:** Keep these features, remove them, or create your own domain-specific features?

---

## 2. Sequence Encoding

### Nucleotide Tokens (`data.py:10-11`)

**Current:**
```python
NUCLEOTIDE_TOKENS = dict(zip(['A', 'C', 'G', 'T'], [0, 1, 2, 3]))
```

**Questions:**
- **DNA/RNA sequences?** Keep as is
- **Protein sequences?** Change to amino acids (20 tokens)
- **Chemical structures?** Need different encoding (SMILES, fingerprints)
- **No sequences?** Remove sequence encoding entirely

**For protein sequences:**
```python
AMINO_ACID_TOKENS = dict(zip(
    ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L',
     'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y'],
    range(20)
))
```

**For non-sequence data:**
- Remove entire `model_inputs()` sequence tokenization logic
- Focus on scalar features only
- Use simpler model architecture (MLP instead of CNN)

---

## 3. Labeling & Filtering

### Activity Threshold (`data.py:121-174`)

**Current:** Uses non-targeting guide distribution to set threshold
```python
threshold = norm.ppf(q=nt_quantile, loc=data_nt['lfc'].mean(), scale=data_nt['lfc'].std())
data['observed_label'] = data['observed_lfc'] < threshold
```

**Questions:**
- Do you have a "negative control" distribution?
- Is your outcome naturally binary, or do you need to threshold?
- What defines "active" in your domain?

**Alternatives:**
```python
# Fixed threshold
data['observed_label'] = data['outcome'] > 0.5

# Median split
median = data['outcome'].median()
data['observed_label'] = data['outcome'] > median

# Domain-specific
data['observed_label'] = (data['fdr'] < 0.1) & (data['effect'] > 0)
```

### Gene/Group Filtering (`data.py:168-174`)

**Current:** Removes genes with < 10% active guides
```python
data[data.guide_type == 'PM'].groupby('gene')['observed_label'].mean()
# Keep genes with active_ratio >= 0.1
```

**Purpose:** Focuses on "essential" genes where CRISPR has effect

**For your use case:**
- Do you need to filter groups/samples?
- What defines a "good" sample to include?
- Minimum number of replicates per group?

---

## 4. Model Architecture

### Current Models:

**Tiger2D** (`models.py:107-127`) - **Default, used in tiger_trainer.py**
- 2D CNN (guide × target alignment matrix)
- Input: One-hot encoded sequences
- Architecture: Conv2D → Pool → Dense layers
- Output: Single value with configurable activation

**Tiger1D** (`models.py:84-104`)
- 1D CNN (concatenated sequences)
- Similar but simpler

### What you need to change:

#### A. If you have sequence data:

Keep CNN architecture but adjust:
```python
# Adjust for your sequence lengths
target_len=23  # Your target sequence length
context_5p=50  # Amount of upstream context
context_3p=50  # Amount of downstream context

# Adjust CNN architecture
filters=32  # Start smaller if less data
kernel_size=(4, 4)  # Adjust for your sequence patterns
```

#### B. If you DON'T have sequence data:

Replace with simple MLP:
```python
class SimpleMLPModel:
    def __init__(self, num_features, output_fn='linear'):
        self.model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(num_features,)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation=output_fn)
        ])
```

#### C. Output activation (`tiger_trainer.py:125`)

**Linked to normalization method:**
- `UnitIntervalNormalization` → `output_fn='sigmoid'` (outputs [0, 1])
- `ZeroMeanUnitVarianceNormalization` → `output_fn='linear'`
- `DepletionRatioNormalization` → `output_fn='softplus'` (positive only)

**Match your normalization to your output activation!**

---

## 5. Train/Validation Splitting

### Current: Target-based splitting (`data.py:177-186`)

```python
targets = data[data.guide_type == 'PM'][['target_seq']].reset_index()
targets['fold'] = np.random.choice(['training', 'validation'], p=[0.9, 0.1])
```

**Purpose:** Ensures same target site isn't in both train and validation

**Options for your data:**
```python
# Random split
data['fold'] = np.random.choice(['training', 'validation'], p=[0.9, 0.1], size=len(data))

# Group-based split (prevent data leakage)
groups = data['sample_id'].unique()
train_groups = np.random.choice(groups, size=int(0.9*len(groups)), replace=False)
data['fold'] = data['sample_id'].apply(lambda x: 'training' if x in train_groups else 'validation')

# Time-based split (if temporal data)
data = data.sort_values('date')
split_idx = int(0.9 * len(data))
data['fold'] = ['training'] * split_idx + ['validation'] * (len(data) - split_idx)

# Stratified split (maintain class balance)
from sklearn.model_selection import train_test_split
train_idx, val_idx = train_test_split(data.index, train_size=0.9, stratify=data['observed_label'])
data['fold'] = 'validation'
data.loc[train_idx, 'fold'] = 'training'
```

---

## 6. Calibration & Scoring

### Post-processing steps:

**1. Calibration** (`tiger_trainer.py:20-28`)
- Adjusts predictions per guide type (PM, SM, DM, TM)
- Uses linear regression slope to correct systematic bias

**For your use case:**
- Do you have categories with systematic bias?
- Do you need calibration per sample/batch?

**2. Scoring** (`tiger_trainer.py:51-67`)
- Maps predictions to [0, 1] using sigmoid transform
- Sets saturation points based on quantiles

**Questions:**
- Do you need predictions as probabilities?
- Or keep as continuous values?

---

## 7. Performance Metrics

### Current metrics (`utils.py:264-301`):
- **Regression:** Slope, Pearson correlation, Spearman correlation
- **Classification:** AUROC, AUPRC (requires `observed_label`)
- **Curves:** ROC and Precision-Recall curves

**What you need:**

| Your Task Type | Recommended Metrics | Keep/Modify? |
|----------------|---------------------|--------------|
| Regression only | Pearson, Spearman, RMSE, MAE | Keep regression, remove classification |
| Classification only | AUROC, AUPRC, Accuracy, F1 | Keep classification, remove regression |
| Both | All metrics | Keep all |

**Modifications needed:**
```python
# If no labels, remove classification metrics
def measure_performance(df, obs_var='observed_value', pred_var='predicted_value'):
    slope, r, rho = regression_metrics(df[obs_var], df[pred_var])
    # Remove AUROC/AUPRC if no labels
    return pd.DataFrame({
        'Pearson': [r],
        'Spearman': [rho],
        'RMSE': [np.sqrt(np.mean((df[obs_var] - df[pred_var])**2))]
    })
```

---

## 8. Hardware & Dependencies

### GPU Configuration (`models.py:12-15`)
```python
for gpu in tf.config.list_physical_devices('GPU'):
    tf.config.experimental.set_memory_growth(gpu, enable=True)
```

**Questions:**
- Do you have GPU access?
- Multiple GPUs? Modify to use all or specific ones
- CPU only? Remove GPU config, may need smaller batch sizes

### Dependencies:
```
tensorflow >= 2.x
pandas
numpy
scipy
scikit-learn
statsmodels
seaborn
matplotlib
```

**Check if you need:**
- Different TensorFlow version
- Additional domain-specific libraries
- Lighter alternatives (e.g., JAX instead of TF)

---

## 9. Hyperparameters to Tune

### In `tiger_trainer.py`:

| Parameter | Current Value | What It Controls |
|-----------|---------------|------------------|
| `NORMALIZATION` | `'UnitInterval'` | How data is scaled |
| `q_neg`, `q_pos` | 1, 99 | Quantile range for normalization |
| `squash` | False | Clip values to [0,1] |
| `training_ratio` | 0.9 | Train/validation split |
| `batch_size` | (in args) | Training batch size |
| `random_seed` | 12345 | Reproducibility |

### Model architecture:
- Number of Conv layers
- Filter sizes: `filters=32`
- Kernel sizes: `kernel_size=(4,4)`
- Dropout rates: `0.25`, `0.1`
- Dense layer sizes: `128`, `32`

**Start with defaults, then tune based on your data size and complexity**

---

## 10. File Paths & Organization

### Current structure:
```
tiger-main/
├── data-processed/          # Preprocessed data (.bz2 files)
│   ├── off-target.bz2
│   └── hap-titration.bz2
├── hugging_face/            # Saved models
│   ├── model/               # TensorFlow saved model
│   ├── calibration_params.pkl
│   └── scoring_params.pkl
├── data.py                  # Data loading
├── normalization.py         # Normalization classes
├── models.py               # Model architectures
├── tiger_trainer.py        # Main training script
└── utils.py                # Helper functions
```

**Make it flexible:**
```python
# Use environment variables or config file
DATA_DIR = os.getenv('DATA_DIR', 'data-processed')
MODEL_DIR = os.getenv('MODEL_DIR', 'saved_models')
```

---

## 11. Common Pitfalls & Solutions

### A. Memory Issues
**Problem:** Large sequences + context = huge tensors

**Solutions:**
```python
# Reduce context size
context_5p = 50  # Instead of 100
context_3p = 50

# Reduce max_context in model_inputs
max_context = 50  # Line 189 in data.py

# Use smaller batch sizes
batch_size = 32  # Instead of 128
```

### B. Class Imbalance
**Problem:** Most guides inactive, few active

**Solutions:**
```python
# In label_and_filter_data, use class weights
class_weights = {0: 1.0, 1: 10.0}  # Weight active class higher

# Or in data.py, add sample_weights column
data['sample_weights'] = data['observed_label'].map({0: 1.0, 1: 10.0})
```

### C. Different Sequence Lengths
**Problem:** Variable-length sequences

**Current:** Uses padding (value=255) and ragged tensors

**Keep:** The padding logic in `model_inputs()` handles this

**Modify:** Adjust padding strategy if needed

### D. Missing Features
**Problem:** Code expects features you don't have

**Solution:** Make features optional
```python
# In model_inputs(), wrap in try-except or check existence
scalar_feats = [f for f in scalar_feats if f in data.columns]
```

---

## 12. Minimal Example for Your Use Case

Here's a skeleton to get started:

```python
# 1. Load your data
def load_my_data(file_path):
    df = pd.read_csv(file_path)

    # Map your columns to TIGER's expected names
    df = df.rename(columns={
        'sample_id': 'gene',
        'treatment_id': 'guide_id',
        'treatment_seq': 'guide_seq',
        'target_site': 'target_seq',
        'outcome': 'observed_lfc',
        'is_active': 'observed_label'
    })

    # Add required columns if missing
    if '5p_context' not in df.columns:
        df['5p_context'] = ''  # Empty if no context
    if '3p_context' not in df.columns:
        df['3p_context'] = ''
    if 'guide_type' not in df.columns:
        df['guide_type'] = 'PM'  # All "perfect match"

    return df

# 2. Choose normalization
from normalization import UnitIntervalNormalization

data = load_my_data('my_data.csv')
normalizer = UnitIntervalNormalization(data, q_neg=5, q_pos=95, squash=False)
data = normalizer.normalize_targets(data)

# 3. Split data
data['fold'] = np.random.choice(['training', 'validation'], p=[0.9, 0.1], size=len(data))

# 4. Prepare inputs
from data import model_inputs

train_data = model_inputs(data[data.fold == 'training'], context=(0, 0), scalar_feats=set())
valid_data = model_inputs(data[data.fold == 'validation'], context=(0, 0), scalar_feats=set())

# 5. Build & train model
from models import build_model, train_model

model = build_model(
    name='Tiger2D',
    target_len=train_data['target_tokens'].shape[1],
    context_5p=0,  # No context
    context_3p=0,
    use_guide_seq=True,
    output_fn='sigmoid'  # Match normalization
)

model = train_model(model, train_data, valid_data, batch_size=64)

# 6. Make predictions & denormalize
from models import test_model

predictions = test_model(model, valid_data)
predictions = normalizer.denormalize_targets_and_predictions(predictions)
```

---

## 13. Critical Decision Checklist

Before starting, decide:

- [ ] **Do I have sequence data?** → If no, replace CNN with MLP
- [ ] **What are my target variables?** → Continuous, binary, or both?
- [ ] **Do I need per-group normalization?** → Or global?
- [ ] **What's my train/test split strategy?** → Random, grouped, temporal?
- [ ] **Do I have negative controls?** → For threshold setting?
- [ ] **What output range do I need?** → [0,1], unbounded, positive only?
- [ ] **Do I need calibration/scoring?** → Or just raw predictions?
- [ ] **What's my evaluation metric?** → AUROC, Pearson, RMSE?
- [ ] **Do I have enough data?** → May need simpler model if small dataset
- [ ] **GPU available?** → Affects batch size and model size

---

## 14. Recommended Reimplementation Order

1. **Start minimal:** Use `NoNormalization` + simple data loading
2. **Test data pipeline:** Ensure `load_data()` → `model_inputs()` works
3. **Train basic model:** Use Tiger1D with no context, no extra features
4. **Add complexity gradually:**
   - Add normalization
   - Add context sequences
   - Add scalar features
   - Add calibration/scoring
5. **Tune hyperparameters:** Once baseline works
6. **Validate thoroughly:** Use multiple evaluation metrics

---

## Key Takeaways

The key is to **start simple** and **add complexity only when needed**. Most projects won't need all of TIGER's features.

### Most Critical Changes:
1. **Column mapping** - Map your data columns to TIGER's expected names
2. **Normalization** - Choose appropriate method for your data distribution
3. **Model architecture** - CNN for sequences, MLP for tabular data
4. **Output activation** - Must match your normalization method
5. **Evaluation metrics** - Choose metrics appropriate for your task type

### TIGER-Specific Features to Consider Removing:
- Guide type handling (PM/SM/DM) if not applicable
- Perfect match (PM) special logic
- CRISPR-specific scalar features
- Calibration per guide type
- Non-targeting control logic

### Universal Features to Keep:
- Normalization framework (very flexible)
- Train/validation splitting
- Model training pipeline
- Performance evaluation
- Denormalization logic

---

## Additional Resources

- **TIGER Paper:** Reference the original publication for theoretical background
- **Data Format:** Check `data-processed/` folder for example data structure
- **Model Architectures:** See `models.py` for all available architectures
- **Normalization Methods:** See `normalization.py` docstring (lines 7-40) for quick reference

---

## 15. Deep Dive: Neural Network Architecture Components

This section provides detailed explanations for adapting Tiger's neural network layers for your own use case. Based on annotations in `layers.py` and `models.py`.

### 15.1 Core Reusable Layers

These layers are **fully reusable** if you're working with sequence data:

| Layer | Location | Purpose | When to Use |
|-------|----------|---------|-------------|
| `OneHotInputParser` | `layers.py:28-46` | Unpacks flat input tensor into structured sequences | Always needed for one-hot encoded sequences |
| `AlignOneHotEncoding1D` | `layers.py:53-65` | Concatenates target/guide along feature dimension [batch, len, 8] | With 1D CNNs or RNNs |
| `AlignOneHotEncoding2D` | `layers.py:72-87` | Stacks target/guide as channels [batch, 4, len, 2] | With 2D CNNs |
| `SequenceSequentialWithNonSequenceBypass` | `layers.py:9-21` | Processes sequences while bypassing scalar features | When combining sequences with scalar features |

**Why keep them:** These handle the tedious packing/unpacking of sequence data and tensor shape transformations.

### 15.2 Understanding Data Packing/Unpacking

**The Problem:** Neural networks expect single flat tensors as input, but the input comprises multiple data types (DNA sequences, guide sequences, scalar features).

**The Solution:** A serialization pattern where `pack_inputs()` flattens everything into one tensor, and `OneHotInputParser` unpacks it back.

#### Packing Example (`models.py:59-85`)

```python
def pack_inputs(self, data: dict):
    # Step 1: Pack target sequence (5' + target + 3' context)
    x = tf.concat([data['5p_tokens'], data['target_tokens'], data['3p_tokens']], axis=1)
    x = tf.reshape(tf.one_hot(x, depth=4), [len(data['target_tokens']), -1])
    # Result: [batch_size, 4*target_len]

    # Step 2: Pack guide sequence (padded to match target)
    if self.input_parser.guide_len > 0:
        pad_5p = 255 * tf.ones([...])  # Padding with special token 255
        pad_3p = 255 * tf.ones([...])
        guide_tokens = tf.concat([pad_5p, data['guide_tokens'], pad_3p], axis=1)
        x = tf.concat([x, tf.reshape(tf.one_hot(guide_tokens, depth=4), [...])], axis=1)
    # Result: [batch_size, 4*target_len + 4*guide_len]

    # Step 3: Pack non-sequence features
    x = self.concatenate_non_sequence_features(data, x, scalar_feats)
    # Final: [batch_size, 4*target_len + 4*guide_len + num_features]
```

**Visual representation:**
```
Input tensor x (flattened):
┌─────────────────┬─────────────────┬──────────────┐
│  Cols 0-119     │  Cols 120-239   │  Cols 240+   │
│  (4×30)         │  (4×30)         │  (variable)  │
│  Target 1-hot   │  Guide 1-hot    │  Scalars     │
└─────────────────┴─────────────────┴──────────────┘
```

#### Unpacking Example (`layers.py:34-46`)

```python
def call(self, x):
    # Parser knows exact positions because lengths were set during __init__

    # Extract columns 0 to 4*target_len
    target_one_hot = x[:, : 4 * self.target_len]
    target_one_hot = tf.reshape(target_one_hot, [tf.shape(x)[0], self.target_len, 4])

    # Extract columns 4*target_len to 4*(target_len + guide_len)
    guide_one_hot = x[:, 4 * self.target_len : 4 * (self.target_len + self.guide_len)]
    guide_one_hot = tf.reshape(guide_one_hot, [tf.shape(x)[0], self.guide_len, 4])

    # Extract remaining columns
    non_sequence_features = x[:, 4 * (self.target_len + self.guide_len):]

    return target_one_hot, guide_one_hot, non_sequence_features
```

**Key insight:** The parser uses stored lengths (`self.target_len`, `self.guide_len`) to know exactly where each data type starts/ends in the flat tensor.

### 15.3 Model Architecture Choices

#### Option 1: Tiger1D (1D CNN) - `models.py:88-104`

**Best for:**
- Sequential patterns (like text)
- Local motifs in DNA/protein sequences
- Faster training

**Architecture:**
```python
layers.AlignOneHotEncoding1D(use_guide_seq)  # Concatenate sequences
    → [batch, length, 8]  # 4 channels for target + 4 for guide
tf.keras.layers.Conv1D(filters=128, kernel_size=5, activation='relu')
    → Detects 5-nucleotide patterns
tf.keras.layers.Flatten()
tf.keras.layers.Dense(128) → Dense(32) → Dense(1)
```

**When NOT to use:** When spatial relationships between two sequences matter (use Tiger2D instead).

#### Option 2: Tiger2D (2D CNN) - `models.py:111-127`

**Best for:**
- Spatial relationships between sequences
- Sequence-sequence interactions (guide-target alignment)
- Treating sequences like "images"

**Architecture:**
```python
layers.AlignOneHotEncoding2D(use_guide_seq)  # Stack sequences as channels
    → [batch, 4, length, 2]  # 4 nucleotides × 2 sequences
tf.keras.layers.Conv2D(filters=32, kernel_size=(4,4))
    → Detects spatial patterns across both sequences
tf.keras.layers.MaxPooling2D(pool_size=(1,2))
tf.keras.layers.Flatten()
tf.keras.layers.Dense(128) → Dense(32) → Dense(1)
```

**Why 2D?** Captures interactions like "when guide has G at position i AND target has C at position i+2."

#### Option 3: Custom MLP (No Sequences)

**Best for:**
- Tabular data without sequences
- When you only have scalar features

**Minimal implementation:**
```python
class SimpleMLPModel:
    def __init__(self, num_features, output_fn='linear'):
        self.model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(num_features,)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation=output_fn)
        ])
```

### 15.4 Output Configuration

**Critical rule:** Output activation must match normalization method!

| Normalization | Output Activation | Output Range | Loss Function |
|---------------|-------------------|--------------|---------------|
| `UnitIntervalNormalization` | `'sigmoid'` | [0, 1] | `'mse'` or `'mae'` |
| `ZeroMeanUnitVarianceNormalization` | `'linear'` | (-∞, +∞) | `'mse'` |
| `DepletionRatioNormalization` | `'softplus'` | [0, +∞) | `'mse'` |
| Binary classification | `'sigmoid'` | [0, 1] | `'binary_crossentropy'` |
| Multi-class | `'softmax'` | Prob distribution | `'categorical_crossentropy'` |

**Why this matters:** Mismatch causes training to fail or produce nonsensical predictions.

### 15.5 SHAP Interpretation (Optional)

**Purpose:** Explains which sequence positions/features contributed most to predictions.

**What it returns:** For each prediction, a contribution score for every input feature.

**Example output:**

| Position | Nucleotide | SHAP Score | Interpretation |
|----------|------------|------------|----------------|
| 5 | A | +0.12 | This 'A' increased prediction by 0.12 |
| 10 | G | -0.08 | This 'G' decreased prediction by 0.08 |
| GC_content | 0.52 | +0.15 | High GC content increased prediction |

**When to use:**
- Understanding what the model learned
- Debugging unexpected predictions
- Discovering biological insights
- Building trust in the model

**Location:** `models.py:301-321` (explain_model function)

**Note:** SHAP is computationally expensive. Only use on small subsets of validation data.

### 15.6 Practical Modifications Guide

#### A. Removing Guide Sequences

If your task doesn't involve guide-target interactions:

```python
# In pack_inputs():
def pack_inputs(self, data: dict):
    # Remove guide sequence logic
    x = data['sequence_tokens']  # Just your main sequence
    x = tf.reshape(tf.one_hot(x, depth=4), [len(data['sequence_tokens']), -1])

    # Add scalar features
    x = self.concatenate_non_sequence_features(data, x, scalar_feats)

    y = data['target_value']
    return x, y

# In model architecture:
layers.AlignOneHotEncoding1D(use_guide_seq=False)  # No guide
```

#### B. Removing Context Regions

If you don't need flanking sequences:

```python
# In initialization:
self.input_parser = layers.OneHotInputParser(
    target_len=sequence_len,
    context_5p=0,  # No context
    context_3p=0,
    use_guide_seq=False,
    pad_guide_seq=False
)

# In pack_inputs():
x = data['sequence_tokens']  # No 5p/3p concatenation
```

#### C. Changing Sequence Type (e.g., Protein)

For protein sequences (20 amino acids instead of 4 nucleotides):

```python
# In data.py, change tokens:
AMINO_ACID_TOKENS = dict(zip(
    'ACDEFGHIKLMNPQRSTVWY',  # 20 standard amino acids
    range(20)
))

# In pack_inputs():
x = tf.reshape(tf.one_hot(x, depth=20), [...])  # depth=20 instead of 4

# In OneHotInputParser.call():
target_one_hot = tf.reshape(target_one_hot, [..., self.target_len, 20])  # 20 instead of 4
```

#### D. Adjusting Architecture Hyperparameters

**Start with these defaults, then tune:**

| Hyperparameter | Small Dataset | Medium Dataset | Large Dataset |
|----------------|---------------|----------------|---------------|
| Conv filters | 32-64 | 64-128 | 128-256 |
| Kernel size | 3-5 | 5-7 | 7-9 |
| Dense units | 32-64 | 64-128 | 128-256 |
| Dropout rate | 0.3-0.5 | 0.2-0.3 | 0.1-0.2 |
| Batch size | 32-64 | 128-256 | 256-2048 |
| Learning rate | 1e-4 | 1e-3 | 1e-3 |

**Signs you need to adjust:**
- **Overfitting** (validation loss > training loss): Increase dropout, reduce model size
- **Underfitting** (both losses high): Increase model capacity, reduce dropout
- **Training unstable**: Reduce learning rate, add batch normalization

### 15.7 Complete Minimal Example

```python
import tensorflow as tf
import layers  # Tiger's reusable layers

class MySequenceModel:
    def __init__(self, sequence_len: int):
        self.sequence_len = sequence_len

        # Initialize parser (no context, no guide)
        self.input_parser = layers.OneHotInputParser(
            target_len=sequence_len,
            context_5p=0,
            context_3p=0,
            use_guide_seq=False,
            pad_guide_seq=False
        )

        # Build 1D CNN architecture
        self.model = tf.keras.Sequential(name='MyModel', layers=[
            layers.SequenceSequentialWithNonSequenceBypass(
                input_parser=self.input_parser,
                sequence_layers=[
                    layers.AlignOneHotEncoding1D(use_guide_seq=False),
                    tf.keras.layers.Conv1D(filters=64, kernel_size=3, activation='relu'),
                    tf.keras.layers.MaxPooling1D(pool_size=2),
                    tf.keras.layers.Conv1D(filters=128, kernel_size=3, activation='relu'),
                    tf.keras.layers.Flatten()
                ]),
            tf.keras.layers.Dense(units=64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(units=32, activation='relu'),
            tf.keras.layers.Dense(1, activation='linear')  # Regression
        ])

    def pack_inputs(self, data: dict):
        """Convert your data to model input format."""
        x = data['sequence_tokens']  # [batch_size, sequence_len]
        x = tf.reshape(tf.one_hot(x, depth=4), [len(data['sequence_tokens']), -1])
        y = data['target_value']
        return x, y

    def compile_and_train(self, train_data, valid_data, epochs=100, batch_size=128):
        """Compile and train the model."""
        # Compile
        self.model.compile(
            optimizer=tf.optimizers.Adam(1e-3),
            loss='mse',
            metrics=['mae']
        )

        # Prepare data
        x_train, y_train = self.pack_inputs(train_data)
        x_valid, y_valid = self.pack_inputs(valid_data)

        # Train
        history = self.model.fit(
            x_train, y_train,
            validation_data=(x_valid, y_valid),
            batch_size=batch_size,
            epochs=epochs,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(patience=20, restore_best_weights=True)
            ],
            verbose=1
        )

        return history

    def predict(self, test_data):
        """Make predictions."""
        x_test, _ = self.pack_inputs(test_data)
        return self.model.predict(x_test)

# Usage
model = MySequenceModel(sequence_len=100)

train_data = {
    'sequence_tokens': train_sequences,  # [N, 100], values 0-3
    'target_value': train_targets        # [N,]
}

valid_data = {
    'sequence_tokens': valid_sequences,
    'target_value': valid_targets
}

history = model.compile_and_train(train_data, valid_data)
predictions = model.predict(test_data)
```

### 15.8 Quick Reference: Which Components to Keep/Modify/Remove

#### ✅ Always Keep (Universal)
- `SequenceSequentialWithNonSequenceBypass` - Handles sequence + scalar features
- Base packing/unpacking pattern
- Model compilation and training loop
- Performance evaluation framework

#### 🔧 Always Modify (Task-Specific)
- `pack_inputs()` - Adapt to your data dictionary keys
- Model architecture - Adjust layers, sizes, activations
- Loss function - Match to your task (regression/classification)
- Output activation - Match to your normalization

#### ❌ Remove if Not Applicable
- Guide sequence logic (CRISPR-specific)
- Context regions (genomic-specific)
- RBP features (CRISPR-specific)
- Guide type handling (PM/SM/DM)
- SHAP explanation (if not needed)

---

**Last Updated:** 2025-12-12
**Version:** 2.0
