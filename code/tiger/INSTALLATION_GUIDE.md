# TIGER Installation Guide

This guide will help you install all required dependencies with the exact versions used by this project.

---

## Prerequisites

- **Python**: 3.8 - 3.10 (recommended: Python 3.9)
- **pip**: Latest version
- **Operating System**: Windows, macOS, or Linux

---

## Installation Methods

### **Method 1: Install from requirements.txt (Recommended)**

This is the fastest and most reliable method:

```bash
# Navigate to the project directory
cd <PATH_TO_PROJECT>\tiger-main\tiger-main

# Install all dependencies at once
pip install -r requirements.txt
```

**Note:** The requirements.txt file specifies these exact versions:
- biopython==1.80
- matplotlib==3.6.2
- pandas==1.5.2
- seaborn==0.12.1
- shap==0.42.1
- sklearn (latest compatible version)
- statsmodels==0.13.5
- streamlit==1.21.0
- tensorflow-probability==0.19.0

---

### **Method 2: Manual Installation (Step-by-step)**

If you prefer to install packages individually or encounter issues:

```bash
# Core scientific computing
pip install numpy==1.23.5
pip install pandas==1.5.2
pip install scipy==1.9.3

# Visualization
pip install matplotlib==3.6.2
pip install seaborn==0.12.1

# Machine Learning - TensorFlow
pip install tensorflow==2.11.0
pip install tensorflow-probability==0.19.0

# Machine Learning - Scikit-learn
pip install scikit-learn==1.2.0

# Statistics
pip install statsmodels==0.13.5

# Bioinformatics
pip install biopython==1.80

# Model interpretability
pip install shap==0.42.1

# Web application (for TIGER web interface)
pip install streamlit==1.21.0
```

---

### **Method 3: Create Virtual Environment (Best Practice)**

Using a virtual environment prevents conflicts with other Python projects:

#### **On Windows:**

```bash
# Navigate to project directory
cd <PATH_TO_PROJECT>\tiger-main\tiger-main

# Create virtual environment
python -m venv tiger_env

# Activate virtual environment
tiger_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### **On macOS/Linux:**

```bash
# Navigate to project directory
cd ~/Downloads/tiger-main/tiger-main

# Create virtual environment
python3 -m venv tiger_env

# Activate virtual environment
source tiger_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Complete Dependency List

Based on code analysis, here are ALL packages used by TIGER:

### **Core Dependencies (Required)**

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | 1.23.5 | Numerical computing |
| pandas | 1.5.2 | Data manipulation |
| scipy | 1.9.3 | Scientific computing |
| tensorflow | 2.11.0 | Deep learning framework |
| tensorflow-probability | 0.19.0 | Probabilistic modeling |
| scikit-learn | 1.2.0 | Machine learning utilities |
| statsmodels | 0.13.5 | Statistical modeling |
| matplotlib | 3.6.2 | Plotting |
| seaborn | 0.12.1 | Statistical visualization |
| biopython | 1.80 | Biological sequence analysis |
| shap | 0.42.1 | Model interpretability |

### **Optional Dependencies**

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.21.0 | Web application interface |

---

## Version Compatibility Notes

### **TensorFlow**

The project uses **TensorFlow 2.11.0**, which is compatible with:
- Python 3.8 - 3.10
- CUDA 11.2 (if using GPU)
- cuDNN 8.1 (if using GPU)

**Important:** TensorFlow 2.11 does NOT support Python 3.11+

### **NumPy**

- Version 1.23.5 is recommended for compatibility with TensorFlow 2.11
- Newer versions (1.24+) may cause compatibility issues

### **Python Version**

**Recommended:** Python 3.9.x

- ✅ Python 3.8: Compatible
- ✅ Python 3.9: **Recommended** (best tested)
- ✅ Python 3.10: Compatible
- ❌ Python 3.11+: **NOT compatible** (TensorFlow 2.11 not supported)

---

## GPU Support (Optional)

If you have an NVIDIA GPU and want to use it for faster training:

### **Install CUDA and cuDNN**

1. **CUDA 11.2**: Download from [NVIDIA CUDA Toolkit Archive](https://developer.nvidia.com/cuda-11-2-0-download-archive)
2. **cuDNN 8.1**: Download from [NVIDIA cuDNN Archive](https://developer.nvidia.com/rdp/cudnn-archive)

### **Install TensorFlow GPU**

```bash
# Instead of regular tensorflow, install:
pip install tensorflow-gpu==2.11.0
```

### **Verify GPU is detected**

```python
import tensorflow as tf
print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
```

---

## Troubleshooting

### **Issue: TensorFlow installation fails**

**Solution 1:** Update pip first
```bash
python -m pip install --upgrade pip
```

**Solution 2:** Install specific wheel
```bash
pip install tensorflow==2.11.0 --no-cache-dir
```

**Solution 3:** Check Python version
```bash
python --version  # Must be 3.8-3.10
```

---

### **Issue: NumPy version conflict**

**Error:** `numpy 1.24.0 is incompatible with tensorflow 2.11.0`

**Solution:**
```bash
pip install numpy==1.23.5 --force-reinstall
```

---

### **Issue: SHAP installation fails**

**Solution:** Install required compilers first

**Windows:**
- Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

**macOS:**
```bash
xcode-select --install
```

**Linux:**
```bash
sudo apt-get install build-essential
```

Then retry:
```bash
pip install shap==0.42.1
```

---

### **Issue: Biopython installation fails**

**Solution:**
```bash
# Install dependencies first
pip install numpy
# Then install biopython
pip install biopython==1.80
```

---

### **Issue: "ModuleNotFoundError" when running code**

**Check installed packages:**
```bash
pip list
```

**Verify specific package:**
```bash
pip show tensorflow
```

**Reinstall missing package:**
```bash
pip install <package-name>==<version>
```

---

## Verification

After installation, verify everything works:

### **Quick Test**

```python
# test_installation.py
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
from Bio import SeqIO
import shap
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
import statsmodels.api as sm

print("✓ NumPy version:", np.__version__)
print("✓ Pandas version:", pd.__version__)
print("✓ TensorFlow version:", tf.__version__)
print("✓ All imports successful!")
print("✓ GPU available:", len(tf.config.list_physical_devices('GPU')) > 0)
```

Run the test:
```bash
python test_installation.py
```

**Expected output:**
```
✓ NumPy version: 1.23.5
✓ Pandas version: 1.5.2
✓ TensorFlow version: 2.11.0
✓ All imports successful!
✓ GPU available: True  (or False if no GPU)
```

---

## Platform-Specific Notes

### **Windows**

- Use PowerShell or Command Prompt
- May need to run as Administrator for some installations
- If using Anaconda, use `conda install` for some packages

### **macOS (Apple Silicon M1/M2)**

- TensorFlow 2.11 has native ARM support
- Install using:
  ```bash
  pip install tensorflow-macos==2.11.0
  pip install tensorflow-metal  # For GPU acceleration
  ```

### **Linux**

- Install system dependencies first:
  ```bash
  sudo apt-get update
  sudo apt-get install python3-dev python3-pip
  ```

---

## Alternative: Conda Environment

If you prefer Conda over pip:

```bash
# Create environment
conda create -n tiger python=3.9

# Activate environment
conda activate tiger

# Install packages
conda install numpy=1.23.5 pandas=1.5.2 matplotlib=3.6.2 seaborn=0.12.1 scikit-learn=1.2.0 scipy=1.9.3
pip install tensorflow==2.11.0 tensorflow-probability==0.19.0
pip install biopython==1.80 shap==0.42.1 statsmodels==0.13.5 streamlit==1.21.0
```

---

## Minimal Installation (Core Only)

If you only want to run the core TIGER model (no web interface, no visualization):

```bash
pip install numpy==1.23.5
pip install pandas==1.5.2
pip install tensorflow==2.11.0
pip install scipy==1.9.3
pip install scikit-learn==1.2.0
pip install statsmodels==0.13.5
```

---

## Summary Commands

**Quick Install (Recommended):**
```bash
cd <PATH_TO_PROJECT>\tiger-main\tiger-main
pip install -r requirements.txt
```

**With Virtual Environment:**
```bash
cd <PATH_TO_PROJECT>\tiger-main\tiger-main
python -m venv tiger_env
tiger_env\Scripts\activate  # On Windows
pip install -r requirements.txt
```

**Verify Installation:**
```bash
python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__)"
python -c "import pandas as pd; print('Pandas:', pd.__version__)"
python -c "import numpy as np; print('NumPy:', np.__version__)"
```

---

## Next Steps

After successful installation:

1. ✅ Test imports (see Verification section)
2. ✅ Download/prepare data (see `data-processed/` folder)
3. ✅ Read [CODE_FLOW_GUIDE.md](CODE_FLOW_GUIDE.md) to understand the codebase
4. ✅ Run TIGER trainer: `python tiger_trainer.py --retrain`

---

**Last Updated:** 2025-12-06
**Tested on:** Python 3.9.x, Windows 10/11, Ubuntu 20.04, macOS 12+
