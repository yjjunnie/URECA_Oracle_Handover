"""
TIGER Installation Verification Script
Run this script after installation to verify all dependencies are correctly installed.
"""

import sys

def test_import(module_name, package_name=None, version_check=None):
    """Test if a module can be imported and optionally check its version."""
    try:
        if package_name:
            module = __import__(package_name)
        else:
            module = __import__(module_name)

        version = getattr(module, '__version__', 'unknown')

        if version_check and version != 'unknown':
            status = "✓" if version.startswith(version_check) else "✗"
            print(f"{status} {module_name:25s} {version:15s} (expected: {version_check})")
        else:
            print(f"✓ {module_name:25s} {version}")

        return True
    except ImportError as e:
        print(f"✗ {module_name:25s} FAILED - {str(e)}")
        return False

def main():
    print("=" * 70)
    print("TIGER Installation Verification")
    print("=" * 70)
    print()

    # Check Python version
    print("Python Version Check:")
    print(f"  Python version: {sys.version}")

    if sys.version_info < (3, 8) or sys.version_info >= (3, 11):
        print("  WARNING: Python 3.8-3.10 is recommended for TensorFlow 2.11")
    else:
        print("  ✓ Python version is compatible")
    print()

    # Test all required packages
    print("Core Dependencies:")
    print("-" * 70)

    results = []

    # Core scientific computing
    results.append(test_import("numpy", version_check="1.23"))
    results.append(test_import("pandas", version_check="1.5"))
    results.append(test_import("scipy", version_check="1.9"))

    print()
    print("Machine Learning:")
    print("-" * 70)

    # TensorFlow
    results.append(test_import("tensorflow", version_check="2.11"))
    results.append(test_import("tensorflow_probability", package_name="tensorflow_probability"))
    results.append(test_import("sklearn", package_name="sklearn"))
    results.append(test_import("shap", version_check="0.42"))

    print()
    print("Statistics:")
    print("-" * 70)

    results.append(test_import("statsmodels", version_check="0.13"))

    print()
    print("Visualization:")
    print("-" * 70)

    results.append(test_import("matplotlib", version_check="3.6"))
    results.append(test_import("seaborn", version_check="0.12"))

    print()
    print("Bioinformatics:")
    print("-" * 70)

    results.append(test_import("Bio", package_name="Bio"))

    print()
    print("Web Interface (Optional):")
    print("-" * 70)

    results.append(test_import("streamlit", version_check="1.21"))

    # GPU Check
    print()
    print("GPU Support:")
    print("-" * 70)

    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"✓ GPU detected: {len(gpus)} device(s)")
            for i, gpu in enumerate(gpus):
                print(f"  GPU {i}: {gpu.name}")
        else:
            print("NOTE: No GPU detected (CPU-only mode)")
            print("  This is fine for testing, but training will be slower")
    except Exception as e:
        print(f"✗ GPU check failed: {e}")

    # Summary
    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)

    total = len(results)
    passed = sum(results)

    if passed == total:
        print(f"✓ All {total} packages installed successfully!")
        print()
        print("Next steps:")
        print("  1. Read CODE_FLOW_GUIDE.md to understand the codebase")
        print("  2. Check data-processed/ folder for data files")
        print("  3. Run: python tiger_trainer.py --retrain")
        return 0
    else:
        print(f"WARNING: only {passed}/{total} packages installed successfully")
        print(f"✗ {total - passed} packages failed")
        print()
        print("Please check INSTALLATION_GUIDE.md for troubleshooting steps")
        return 1

if __name__ == "__main__":
    sys.exit(main())
