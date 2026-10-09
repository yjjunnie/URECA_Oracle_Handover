# Column Explanations for Tiger Predictions Data

This document explains all columns in the Tiger predictions PKL/CSV files.

## Index Columns (from Multi-Index)

### 1. `context`
- **Type:** Tuple (e.g., `(1, 1)`)
- **Meaning:** Amount of flanking genomic sequence around the target
  - First value: Number of nucleotides of 5' context (upstream)
  - Second value: Number of nucleotides of 3' context (downstream)
- **Example:** `(1, 1)` = 1 nucleotide on each side of the target sequence

### 2. `features`
- **Type:** Tuple of feature names or 'None'
- **Meaning:** Which specific features were used for this prediction
- **Examples:**
  - `None` - No additional features (baseline model)
  - `('loc_cds', 'loc_utr_3p', 'loc_utr_5p', 'log_gene_len')` - Target location features
  - `('mfe',)` - Minimum free energy feature

### 3. `filter-method`
- **Type:** String
- **Meaning:** Gene filtering method applied before training
- **Common values:**
  - `'NoFilter'` - No filtering applied
  - `'MinActiveRatio'` - Filter genes by minimum active guide ratio

### 4. `loss`
- **Type:** String
- **Meaning:** Loss function used during model training
- **Common values:**
  - `'log_cosh'` - Log-cosh loss function (smooth approximation of L1 loss)

### 5. `min active ratio`
- **Type:** Float
- **Meaning:** Minimum ratio of active guides required per gene for filtering
- **Example:** `0.1` means genes must have at least 10% active guides

### 6. `model`
- **Type:** String
- **Meaning:** Model architecture used
- **Common values:**
  - `'Tiger2D'` - Tiger model with 2D convolutions
  - `'Tiger1D'` - Tiger model with 1D convolutions

### 7. `normalization`
- **Type:** String
- **Meaning:** Normalization method applied to training targets
- **Common values:**
  - `'FrequentistQuantile'` - Quantile-based normalization
  - `'No'` - No normalization

### 8. `normalization kwargs`
- **Type:** String (dictionary representation)
- **Meaning:** Parameters for the normalization method
- **Example:** `"{'q_loc': 50, 'q_neg': 10, 'q_pos': 90}"`
  - `q_loc=50` - Use 50th percentile (median) as location
  - `q_neg=10` - Use 10th percentile for negative controls
  - `q_pos=90` - Use 90th percentile for positive controls

### 9. `non-targeting quantile`
- **Type:** Float
- **Meaning:** Quantile threshold for non-targeting control guides
- **Example:** `0.01` means use 1st percentile of non-targeting guides

### 10. `training utilization`
- **Type:** Float
- **Meaning:** Fraction of training data used (for ablation studies)
- **Example:** `1.0` means 100% of training data was used

### 11. `feature group`
- **Type:** String
- **Meaning:** Category/group name for the features used
- **Values:**
  - `'none'` - No additional features (baseline)
  - `'target location'` - Gene location features (CDS, UTR, etc.)
  - `'junction proximity'` - Distance to splice junctions
  - `'guide secondary structure'` - Guide RNA structure features
  - `'guide MFE'` - Guide minimum free energy
  - `'hybridization MFE'` - Guide-target hybridization energy
  - `'target accessibility'` - Target RNA unpaired probability

---

## Data Columns

### Guide/Target Information

#### `target_seq`
- **Type:** String (23 nucleotides)
- **Meaning:** The target RNA sequence that the guide is designed to bind to
- **Example:** `'AAAACTACCAAGCTCTTGACGCA'`

#### `gene`
- **Type:** String
- **Meaning:** Gene symbol/name that the target belongs to
- **Example:** `'CDC5L'`, `'RPA1'`, `'SNRNP200'`

#### `guide_id`
- **Type:** String
- **Meaning:** Unique identifier for the guide RNA
- **Format:** `crRNA####:####-####` (crRNA ID : position range)
- **Example:** `'crRNA0872:988-1010'`

#### `guide_seq`
- **Type:** String (23 nucleotides)
- **Meaning:** The guide RNA sequence (spacer sequence)
- **Note:** Usually the reverse complement of the target sequence for PM guides
- **Example:** `'TTTTGATGGTTCGAGAACTGCGT'`

#### `guide_type`
- **Type:** String
- **Meaning:** Type of guide based on mismatches to target
- **Values:**
  - `'PM'` - Perfect Match (0 mismatches)
  - `'SM'` - Single Mismatch (1 mismatch)
  - `'DM'` - Double Mismatch (2 mismatches)
  - `'TM'` - Triple Mismatch (3 mismatches)
  - `'RTM'` - Reverse Triple Mismatch
  - `'RDM'` - Reverse Double Mismatch

---

### Observed Values (Experimental Data)

#### `observed_lfc`
- **Type:** Float
- **Meaning:** **Observed Log Fold Change** from CRISPR screen
- **Calculation:** Mean of biological replicates
- **Interpretation:**
  - **Negative values** → Guide reduced gene expression (effective/active)
  - **Positive values** → Guide increased/maintained expression (inactive)
  - **More negative** → More effective guide
- **Range:** Typically -6 to +2
- **Unit:** log2 scale

#### `observed_lfc_normalized`
- **Type:** Float
- **Meaning:** Normalized version of `observed_lfc`
- **Purpose:** Per-gene normalization to account for gene-specific effects
- **Method:** Depends on normalization method (e.g., FrequentistQuantile)

#### `observed_label`
- **Type:** Integer (0 or 1)
- **Meaning:** Binary classification of guide activity
- **Values:**
  - `1` = Active/effective guide (observed_lfc < threshold)
  - `0` = Inactive/ineffective guide (observed_lfc >= threshold)
- **Threshold:** Typically determined by non-targeting guide distribution

#### `observed_pm_lfc`
- **Type:** Float
- **Meaning:** Observed LFC of the **Perfect Match (PM)** guide for this target
- **Purpose:** Used to calculate relative activity of mismatched guides
- **Note:** For PM guides, this equals `observed_lfc`

#### `observed_pm_lfc_normalized`
- **Type:** Float
- **Meaning:** Normalized version of `observed_pm_lfc`

---

### Predicted Values (Model Output)

#### `predicted_lfc`
- **Type:** Float
- **Meaning:** **Model-predicted Log Fold Change**
- **Purpose:** Tiger model's prediction of guide effectiveness
- **Interpretation:** Same as `observed_lfc` (more negative = more effective)
- **Note:** Raw prediction before denormalization

#### `predicted_lfc_normalized`
- **Type:** Float
- **Meaning:** Normalized version of `predicted_lfc`
- **Note:** Usually same as `predicted_lfc` if model outputs normalized values

#### `predicted_pm_lfc`
- **Type:** Float
- **Meaning:** Predicted LFC of the **Perfect Match (PM)** guide for this target
- **Purpose:** Used to predict relative activity of mismatched guides
- **Note:** For PM guides, this equals `predicted_lfc`

#### `predicted_pm_lfc_normalized`
- **Type:** Float
- **Meaning:** Normalized version of `predicted_pm_lfc`

---

## Understanding the Data Flow

### 1. Raw Experimental Data
- CRISPR screen performed with guide RNAs
- Cell viability/abundance measured over time
- Log fold change (LFC) calculated per replicate

### 2. Data Processing
```
observed_lfc = mean(lfc_r1, lfc_r2, lfc_r3)
observed_label = 1 if observed_lfc < threshold else 0
```

### 3. Normalization
```
observed_lfc_normalized = normalize_per_gene(observed_lfc)
```

### 4. Model Training
- Input: Sequences + features
- Target: `observed_lfc_normalized`
- Output: `predicted_lfc`

### 5. Denormalization
```
predicted_lfc = denormalize(predicted_lfc_normalized)
```

### 6. Off-Target Analysis
- PM guides serve as reference
- Mismatched guides compared to their PM parent
- Calculate: `observed_lfc - observed_pm_lfc` (relative activity)

---

## Example Interpretation

Let's look at an example row:

```
gene: CDC5L
guide_type: PM
observed_lfc: 0.075706
observed_label: 0
predicted_lfc: 0.082728
feature group: none
```

**Interpretation:**
- This is a **Perfect Match** guide targeting gene **CDC5L**
- The guide has an **observed LFC of 0.076** (slightly positive)
- It's labeled as **inactive** (label = 0) because LFC is not negative enough
- The model **predicted LFC of 0.083**, very close to observed
- This prediction used **no additional features** (baseline model)

---

## Key Metrics for Evaluation

### Regression Metrics
- **Pearson correlation** between `predicted_lfc` and `observed_lfc`
- **Spearman correlation** for rank-based comparison
- **RMSE** (Root Mean Squared Error)

### Classification Metrics
- **AUROC** - Area Under ROC Curve (using `observed_label`)
- **AUPRC** - Area Under Precision-Recall Curve
- Uses `predicted_lfc` as continuous score for classification

### Off-Target Analysis
- Compare PM vs mismatch guides
- Calculate specificity ratios: `2^(predicted_pm_lfc - predicted_lfc)`

---

## Common Questions

**Q: Why are there both normalized and non-normalized versions?**
A: Models train on normalized data (for stability), but predictions are denormalized for interpretation.

**Q: What does a negative predicted_lfc mean?**
A: More negative = more effective guide (greater gene knockdown).

**Q: How do I filter for good guides?**
A: Look for guides with low (negative) `predicted_lfc` or high `observed_label` (if using classification).

**Q: Why are there 7 copies of each guide?**
A: One for each feature group to test which features improve predictions.

**Q: What's the difference between observed_lfc and observed_pm_lfc?**
A: For PM guides they're the same. For mismatches, `observed_pm_lfc` is their PM parent's value.
