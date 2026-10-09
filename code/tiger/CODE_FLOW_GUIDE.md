# TIGER Project: Code Flow Guide

This guide explains how to understand the TIGER codebase by following the execution flow from start to finish.

---

## Table of Contents
1. [Quick Overview](#quick-overview)
2. [Main Entry Point](#main-entry-point)
3. [Detailed Execution Flow](#detailed-execution-flow)
4. [File Dependencies Map](#file-dependencies-map)
5. [Reading Order Recommendation](#reading-order-recommendation)
6. [Key Concepts to Understand](#key-concepts-to-understand)
7. [Debugging Flow](#debugging-flow)

---

## Quick Overview

**The TIGER pipeline in 5 steps:**
1. **Load & Label Data** → `data.py`
2. **Normalize Data** → `normalization.py`
3. **Build Model** → `models.py`, `layers.py`
4. **Train Model** → `models.py`, `callbacks.py`
5. **Evaluate & Post-process** → `tiger_trainer.py`, `utils.py`

**Start here:** `tiger_trainer.py` (main script)

---

## Main Entry Point

### `tiger_trainer.py` - The Orchestrator

This is the **main execution script**. Everything flows through here.

**Run it with:**
```bash
python tiger_trainer.py --retrain
```

**What it does:**
1. Loads and preprocesses data
2. Normalizes target values
3. Builds and trains the model
4. Generates predictions
5. Calibrates and scores predictions
6. Evaluates performance

---

## Detailed Execution Flow

Follow this sequence to understand the complete pipeline:

### **STEP 1: Script Initialization** (`tiger_trainer.py:86-101`)

```python
if __name__ == '__main__':
    # Parse command-line arguments
    parser = utils.common_parser_arguments()
    args = utils.parse_common_arguments(parser)

    # Set random seed for reproducibility
    tf.keras.utils.set_random_seed(args.random_seed)
```

**What happens:**
- Command-line arguments parsed (`--retrain`, `--batch_size`, etc.)
- Random seed set for reproducibility
- TensorFlow determinism enabled

**Files involved:** `utils.py`

---

### **STEP 2: Data Loading** (`tiger_trainer.py:104`)

```python
data = load_data(dataset='off-target', pm_only=False, indels=False)
```

**→ Jumps to: `data.py:70-118` - `load_data()`**

**What happens:**
1. Reads pickled data file: `data-processed/off-target.bz2`
2. Filters by guide type (PM, SM, DM, etc.) if requested
3. Applies log transformation to certain features
4. Returns: `(data, data_nt)` - targeting and non-targeting data

**Key data structure returned:**
```python
DataFrame with columns:
- gene, guide_id, guide_seq, target_seq, guide_type
- 5p_context, 3p_context
- lfc_r1, lfc_r2, lfc_r3 (replicate measurements)
- Various scalar features (mfe, loc_utr_5p, etc.)
```

**Files involved:** `data.py`

---

### **STEP 3: Labeling & Filtering** (`tiger_trainer.py:105`)

```python
data = label_and_filter_data(*data, method='NoFilter')
```

**→ Jumps to: `data.py:121-174` - `label_and_filter_data()`**

**What happens:**
1. **Compute activity threshold** from non-targeting guides
2. **Average replicates**: `observed_lfc = mean(lfc_r1, lfc_r2, lfc_r3)`
3. **Binary labeling**: `observed_label = (observed_lfc < threshold)`
4. **Filter genes** with low active guide ratio (if method='MinActiveRatio')

**Key additions to data:**
- `observed_lfc` column (averaged outcome)
- `observed_label` column (binary active/inactive)

**Files involved:** `data.py`, uses `scipy.stats.norm`

---

### **STEP 4: Train/Validation Split** (`tiger_trainer.py:106`)

```python
data = training_validation_split_targets(data, train_ratio=0.9)
```

**→ Jumps to: `data.py:177-186` - `training_validation_split_targets()`**

**What happens:**
1. Extracts unique target sites (from PM guides)
2. Randomly assigns each target to 'training' or 'validation'
3. Adds `fold` column to data

**Why target-based?** Prevents data leakage - same target site won't appear in both training and validation

**Key addition to data:**
- `fold` column ('training' or 'validation')

**Files involved:** `data.py`

---

### **STEP 5: Normalization Setup** (`tiger_trainer.py:109-110`)

```python
normalizer = get_normalization_object(NORMALIZATION)(data, **NORMALIZATION_KWARGS)
data = normalizer.normalize_targets(data)
```

**→ Jumps to: `normalization.py`**

**What happens:**

**5a. Get normalization class** (`normalization.py:42-60`)
```python
get_normalization_object('UnitInterval')  # Returns UnitIntervalNormalization class
```

**5b. Initialize normalizer** (`normalization.py:136-153`)
```python
UnitIntervalNormalization(data, q_neg=1, q_pos=99, squash=False)
```
- Stores original `observed_lfc` values
- Computes per-gene quantiles (1st and 99th percentile)
- Calculates location and scale parameters

**5c. Normalize targets** (`normalization.py:155-161`)
```python
normalizer.normalize_targets(data)
```
- Transforms `observed_lfc` to approximately [0, 1] range
- Formula: `(value - location) / scale`
- Optionally clips to [0, 1] if `squash=True`

**Key transformation:**
```
Original LFC: -3.5, -2.1, 0.2, 1.5
↓ (after normalization)
Normalized: 0.05, 0.23, 0.61, 0.95
```

**Files involved:** `normalization.py`

---

### **STEP 6: Prepare Model Inputs** (`tiger_trainer.py:113-115`)

```python
context = (hf.CONTEXT_5P, hf.CONTEXT_3P)
train_data = model_inputs(data[data.fold == 'training'], context=context, scalar_feats=set())
valid_data = model_inputs(data[data.fold == 'validation'], context=context, scalar_feats=set())
```

**→ Jumps to: `data.py:189-286` - `model_inputs()`**

**What happens:**

**6a. Sequence tokenization**
- Convert nucleotide sequences to integer codes:
  - `'A'` → 0, `'C'` → 1, `'G'` → 2, `'T'` → 3
  - Unknown/padding → 255

**6b. Create ragged tensors**
- Handle variable-length sequences
- Pad to fixed lengths using padding value 255

**6c. Assemble input dictionary**
```python
inputs = {
    # Identifiers
    'gene': TensorFlow constant,
    'target_seq': TensorFlow constant,
    'guide_seq': TensorFlow constant,
    'guide_type': TensorFlow constant,

    # Tokenized sequences (as uint8 arrays)
    'target_tokens': [batch_size, 23],
    'guide_tokens': [batch_size, ~20],
    '5p_tokens': [batch_size, context_5p],
    '3p_tokens': [batch_size, context_3p],

    # Target values
    'observed_lfc': [batch_size],
    'observed_label': [batch_size],
}
```

**Key transformation:**
```
Sequence: "AGCT"
↓
Tokens: [0, 2, 1, 3]
↓
Tensor: tf.constant([0, 2, 1, 3], dtype=tf.uint8)
```

**Files involved:** `data.py`, uses `tensorflow`

---

### **STEP 7: Build Model** (`tiger_trainer.py:118-126`)

```python
tiger = build_model(
    name='Tiger2D',
    target_len=train_data['target_tokens'].shape[1],
    context_5p=train_data['5p_tokens'].shape[1],
    context_3p=train_data['3p_tokens'].shape[1],
    use_guide_seq=True,
    loss_fn='log_cosh',
    output_fn=normalizer.output_fn,  # 'sigmoid' for UnitIntervalNormalization
)
```

**→ Jumps to: `models.py` and `layers.py`**

**What happens:**

**7a. Select model class** (`models.py:build_model()`)
- `name='Tiger2D'` → Uses `Tiger2D` class

**7b. Initialize Tiger2D** (`models.py:107-127`)

Creates a Sequential model with:

```python
layers = [
    # Layer 1: Parse and align sequences
    SequenceSequentialWithNonSequenceBypass(
        sequence_layers=[
            AlignOneHotEncoding2D(use_guide_seq),  # Creates guide×target alignment matrix
            Conv2D(32, (4,4), activation='relu'),   # Detect sequence patterns
            Conv2D(32, (4,4), activation='relu'),   # Learn higher-level features
            MaxPool2D((1,2)),                       # Downsample
            Flatten(),                              # Convert to 1D
            Dropout(0.25),                          # Regularization
        ]
    ),
    # Layer 2: Dense layers
    Dense(128, activation='sigmoid'),
    Dropout(0.1),
    Dense(32, activation='sigmoid'),
    Dropout(0.1),
    Dense(1, activation='sigmoid'),  # output_fn from normalizer
]
```

**Architecture visualization:**
```
Guide Seq (one-hot) ──┐
                       ├─> 2D Alignment Matrix → Conv2D → Conv2D → Pool → Flatten
Target Seq (one-hot) ─┘                                                      │
                                                                             ↓
Scalar Features ────────────────────────────────────────────────────────> Concat
                                                                             │
                                                                             ↓
                                                                    Dense → Dense → Output
```

**7c. Compile model**
- Loss function: `log_cosh` (smooth version of MAE)
- Optimizer: Adam with learning rate schedule
- Metrics: MSE, MAE

**Files involved:** `models.py`, `layers.py`

---

### **STEP 8: Train Model** (`tiger_trainer.py:129-132`)

```python
if args.retrain or not os.path.exists(model_path):
    tiger = train_model(tiger, train_data, valid_data, args.batch_size)
    tiger.model.save(model_path)
```

**→ Jumps to: `models.py:train_model()`**

**What happens:**

**8a. Create TensorFlow datasets**
```python
# Convert dict of tensors to tf.data.Dataset
train_dataset = tf.data.Dataset.from_tensor_slices(train_data)
train_dataset = train_dataset.shuffle(10000).batch(batch_size)
```

**8b. Setup callbacks** (`callbacks.py`)
```python
callbacks = [
    PerformanceCallback(valid_data),  # Custom: computes Pearson correlation each epoch
    EarlyStopping(patience=10),       # Stop if no improvement
    ReduceLROnPlateau(patience=5),    # Reduce learning rate if plateauing
]
```

**8c. Train the model**
```python
tiger.model.fit(
    x=train_dataset,
    epochs=100,
    validation_data=valid_dataset,
    callbacks=callbacks
)
```

**Training loop (each epoch):**
1. Forward pass on batch
2. Compute loss
3. Backpropagation
4. Update weights
5. Evaluate on validation set
6. Check callbacks (early stopping, LR schedule)

**Files involved:** `models.py`, `callbacks.py`

---

### **STEP 9: Generate Predictions** (`tiger_trainer.py:139`)

```python
df_tap = test_model(tiger, valid_data)
```

**→ Jumps to: `models.py:test_model()`**

**What happens:**

**9a. Make predictions**
```python
predictions = tiger.model.predict(valid_data)
```

**9b. Assemble DataFrame**
```python
df = pd.DataFrame({
    'gene': valid_data['gene'],
    'guide_seq': valid_data['guide_seq'],
    'target_seq': valid_data['target_seq'],
    'guide_type': valid_data['guide_type'],
    'observed_lfc': valid_data['observed_lfc'],  # Normalized
    'observed_label': valid_data['observed_label'],
    'predicted_lfc': predictions.flatten(),  # Model output (normalized)
})
```

**9c. Denormalize** (if normalizer provided)
```python
df = normalizer.denormalize_targets_and_predictions(df)
```

This restores original scale:
- `observed_lfc` → original values
- `observed_lfc_normalized` → normalized values
- `predicted_lfc` → denormalized predictions
- `predicted_lfc_normalized` → normalized predictions

**Files involved:** `models.py`, `normalization.py`

---

### **STEP 10: Calibration** (`tiger_trainer.py:146-149`)

```python
calibration_params = calibrate_tiger(df_tap.copy())
test_calibration(df_tap, calibration_params)
```

**→ Jumps to: `tiger_trainer.py:20-48`**

**What happens:**

**10a. Calibrate per guide type** (`calibrate_tiger()`)
```python
for num_mismatches in [0, 1, 2, 3]:
    # Fit linear regression: observed ~ predicted
    slope = measure_performance(df[matching guides])['Slope']
    # Store slope for this mismatch level
```

**10b. Apply calibration** (`test_calibration()`)
```python
# Adjust predictions based on guide type
for each guide:
    calibrated_prediction = slope * original_prediction
```

**Why?** Different guide types have systematic biases (e.g., single mismatches are consistently over-predicted)

**Files involved:** `tiger_trainer.py`, `hugging_face/tiger.py`

---

### **STEP 11: Scoring** (`tiger_trainer.py:152-155`)

```python
scoring_params = score_tiger(df_tap.copy(), args.sat_quant_active, args.sat_quant_inactive)
test_scoring(df_tap, scoring_params)
```

**→ Jumps to: `tiger_trainer.py:51-83`**

**What happens:**

**11a. Compute sigmoid parameters** (`score_tiger()`)
```python
# Map quantiles to sigmoid curve
lfc_active = quantile(predicted_lfc, 0.05)   # Low LFC = active
lfc_inactive = quantile(predicted_lfc, 0.95) # High LFC = inactive

# Solve for sigmoid: score = 1 / (1 + exp(a*lfc + b))
a, b = fit_sigmoid_parameters(lfc_active, lfc_inactive)
```

**11b. Transform predictions** (`test_scoring()`)
```python
score = sigmoid(a * predicted_lfc + b)  # Maps to [0, 1]
```

**Result:** Predictions become interpretable probabilities/scores

**Files involved:** `tiger_trainer.py`, `hugging_face/tiger.py`

---

### **STEP 12: Performance Evaluation** (throughout)

```python
measure_performance(df)
```

**→ Jumps to: `utils.py:264-301`**

**What happens:**

**12a. Regression metrics**
```python
# Pearson correlation
r, p_value = pearsonr(observed, predicted)

# Spearman correlation
rho, p_value = spearmanr(observed, predicted)

# Linear regression slope
slope, intercept = linregress(observed, predicted)
```

**12b. Classification metrics** (if labels available)
```python
# ROC curve
fpr, tpr, _ = roc_curve(observed_label, predicted_lfc)
auroc = auc(fpr, tpr)

# Precision-Recall curve
precision, recall, _ = precision_recall_curve(observed_label, predicted_lfc)
auprc = auc(recall, precision)
```

**12c. Print results**
```
Pearson: 0.7234 | Spearman: 0.7102 | AUROC: 0.8456 | AUPRC: 0.7891
```

**Files involved:** `utils.py`, uses `scipy.stats`, `sklearn.metrics`

---

### **STEP 13: Visualization** (`tiger_trainer.py:142-167`)

```python
titration_confusion_matrix(titration_ratio(df), title='...')
plt.show()
```

**→ Jumps to: `tiger_figures.py`**

**What happens:**
- Creates confusion matrices comparing observed vs predicted guide activity
- Generates ROC curves
- Plots calibration curves

**Files involved:** `tiger_figures.py`, uses `matplotlib`, `seaborn`

---

## File Dependencies Map

```
tiger_trainer.py (MAIN ENTRY POINT)
    │
    ├─> data.py
    │   ├─> load_data()
    │   ├─> label_and_filter_data()
    │   ├─> training_validation_split_targets()
    │   └─> model_inputs()
    │
    ├─> normalization.py
    │   ├─> get_normalization_object()
    │   ├─> Normalization (base class)
    │   └─> UnitIntervalNormalization (and other subclasses)
    │
    ├─> models.py
    │   ├─> build_model()
    │   ├─> train_model()
    │   ├─> test_model()
    │   └─> Tiger2D, Tiger1D (model classes)
    │       └─> layers.py
    │           ├─> AlignOneHotEncoding2D
    │           ├─> SequenceSequentialWithNonSequenceBypass
    │           └─> Custom Keras layers
    │
    ├─> callbacks.py
    │   └─> PerformanceCallback
    │
    ├─> utils.py
    │   ├─> measure_performance()
    │   ├─> regression_metrics()
    │   └─> classification_metrics()
    │
    ├─> tiger_figures.py
    │   └─> titration_confusion_matrix()
    │
    └─> hugging_face/tiger.py
        ├─> calibrate_predictions()
        └─> score_predictions()
```

---

## Reading Order Recommendation

To understand the codebase, read files in this order:

### **Phase 1: Core Concepts (Start Here)**
1. **`normalization.py`** - Understand data preprocessing
   - Read the docstring (lines 7-40) first
   - Then base `Normalization` class
   - Then `UnitIntervalNormalization` (what's actually used)

2. **`data.py`** - Understand data structure
   - Start with column definitions (lines 13-58)
   - Read `load_data()` to see data format
   - Read `model_inputs()` to see TensorFlow conversion

### **Phase 2: Model Architecture**
3. **`layers.py`** - Custom TensorFlow layers
   - Focus on `AlignOneHotEncoding2D` (creates guide×target matrix)
   - Understand input parsing

4. **`models.py`** - Model definition
   - Read `Tiger2D` class to see architecture
   - Understand `build_model()` function

### **Phase 3: Training Pipeline**
5. **`callbacks.py`** - Training monitoring
   - Understand `PerformanceCallback`

6. **`models.py`** - Training functions
   - Read `train_model()` to see training loop

### **Phase 4: Evaluation**
7. **`utils.py`** - Performance metrics
   - Read `measure_performance()`
   - Understand regression vs classification metrics

### **Phase 5: Main Pipeline**
8. **`tiger_trainer.py`** - Complete workflow
   - Now read the entire main script
   - You'll understand what each line does

### **Optional: Advanced Topics**
9. **`hugging_face/tiger.py`** - Post-processing
10. **`tiger_figures.py`** - Visualization

---

## Key Concepts to Understand

### 1. **Normalization Philosophy**
- **Why:** Neural networks train better on normalized data
- **Per-gene normalization:** Each gene has different activity range
- **Match output activation:** Sigmoid output requires [0,1] normalized targets

### 2. **Sequence Encoding**
- **Tokenization:** Convert ACGT → 0123
- **One-hot encoding:** [0,1,2,3] → 4D binary vectors
- **2D Alignment:** Guide×Target matrix shows base pairing

### 3. **Train/Val Split Strategy**
- **Target-based splitting:** Prevents data leakage
- **Why not random?** Same target with different guides would appear in both sets

### 4. **Model Architecture**
- **CNN for sequences:** Learns motifs (like "GC-rich" or "polyT")
- **2D convolution:** Captures guide-target interactions
- **Dense layers:** Combines features for final prediction

### 5. **Post-processing Pipeline**
- **Calibration:** Fixes systematic bias per guide type
- **Scoring:** Maps to interpretable probabilities
- **Why needed?** Raw model outputs may not be well-calibrated

---

## Debugging Flow

### If you want to debug or modify:

**Scenario 1: "I want to change how data is loaded"**
→ Modify `data.py:load_data()`

**Scenario 2: "I want to try different normalization"**
→ Change `NORMALIZATION` in `tiger_trainer.py:16`
→ Or create new class in `normalization.py`

**Scenario 3: "I want to modify model architecture"**
→ Edit `Tiger2D` class in `models.py:107-127`

**Scenario 4: "I want different metrics"**
→ Modify `utils.py:measure_performance()`

**Scenario 5: "Training isn't working"**
→ Check `callbacks.py` - adjust early stopping patience
→ Check `models.py:train_model()` - adjust learning rate

**Scenario 6: "I want to add new features"**
→ Add to `SCALAR_FEATS` in `data.py:58`
→ Ensure features in your data file
→ Pass to `model_inputs(..., scalar_feats={new_feature})`

---

## Execution Timeline

Here's what happens when you run `python tiger_trainer.py --retrain`:

```
[0s] Parse arguments, set random seed
[1s] Load data from data-processed/off-target.bz2
[2s] Label guides as active/inactive, filter genes
[3s] Split into train/validation by target sites
[4s] Initialize normalizer, compute per-gene quantiles
[5s] Normalize observed_lfc values
[6s] Convert sequences to tokens, create TensorFlow tensors
[7s] Build Tiger2D model architecture
[8s] Compile model with loss function and optimizer
[10s] Start training (100 epochs max)
    [10s - 5min] Training loop with early stopping
[5min] Generate predictions on validation set
[5min] Denormalize predictions back to original scale
[5min] Calibrate predictions per guide type
[5min] Score predictions using sigmoid transform
[5min] Evaluate performance (Pearson, AUROC, etc.)
[5min] Generate visualization plots
[5min] Save model and parameters
```

---

## Quick Reference: Where is...?

| What | File | Function/Class |
|------|------|----------------|
| Main execution | `tiger_trainer.py` | `if __name__ == '__main__'` |
| Data loading | `data.py` | `load_data()` |
| Binary labeling | `data.py` | `label_and_filter_data()` |
| Sequence tokenization | `data.py` | `model_inputs()` |
| Normalization logic | `normalization.py` | `UnitIntervalNormalization` |
| Model architecture | `models.py` | `Tiger2D.__init__()` |
| Training loop | `models.py` | `train_model()` |
| Prediction generation | `models.py` | `test_model()` |
| Performance metrics | `utils.py` | `measure_performance()` |
| Calibration | `tiger_trainer.py` | `calibrate_tiger()` |
| Scoring | `tiger_trainer.py` | `score_tiger()` |
| Custom layers | `layers.py` | Various classes |

---

## Summary: The Complete Pipeline

```
Raw Data (.bz2)
    ↓ load_data()
DataFrame with sequences + replicates
    ↓ label_and_filter_data()
DataFrame with observed_lfc + observed_label
    ↓ training_validation_split_targets()
DataFrame with fold assignments
    ↓ normalize_targets()
Normalized DataFrame (LFCs in [0, 1])
    ↓ model_inputs()
TensorFlow tensors (tokenized sequences)
    ↓ build_model()
Tiger2D CNN architecture
    ↓ train_model()
Trained model weights
    ↓ test_model()
Predictions (normalized)
    ↓ denormalize_targets_and_predictions()
Predictions (original scale)
    ↓ calibrate_tiger()
Calibrated predictions
    ↓ score_tiger()
Scored predictions (probabilities)
    ↓ measure_performance()
Performance metrics (Pearson, AUROC, etc.)
```

---

**Last Updated:** 2025-12-06
**Version:** 1.0
