import pickle
import pandas as pd
import sys
import warnings

warnings.filterwarnings('ignore')

# Monkey-patch for pandas 2.0+ compatibility with old pickle files
if not hasattr(pd, 'Float64Index'):
    pd.Float64Index = pd.Index
if not hasattr(pd, 'Int64Index'):
    pd.Int64Index = pd.Index
if not hasattr(pd, 'UInt64Index'):
    pd.UInt64Index = pd.Index

# Also patch in the core.indexes modules
if not hasattr(pd.core.indexes, 'numeric'):
    class NumericCompat:
        Float64Index = pd.Index
        Int64Index = pd.Index
        UInt64Index = pd.Index
    pd.core.indexes.numeric = NumericCompat()
    sys.modules['pandas.core.indexes.numeric'] = NumericCompat()

# Load the pickle file
pkl_path = r'<PATH_TO_PROJECT>\tiger-main\tiger_full\off-target\feature-groups-cumulative\no_indels\targets\predictions.pkl'

print("Loading pickle file...")
with open(pkl_path, 'rb') as f:
    data = pickle.load(f)

print("\n" + "="*100)
print("INDEX STRUCTURE ANALYSIS")
print("="*100)

# Show index information
print(f"\nIndex type: {type(data.index)}")
print(f"Index names: {data.index.names}")
print(f"\nNumber of index levels: {data.index.nlevels}")

print("\n" + "="*100)
print("INDEX LEVEL DETAILS:")
print("="*100)

for i, name in enumerate(data.index.names):
    unique_values = data.index.get_level_values(i).unique()
    print(f"\nLevel {i}: '{name}'")
    print(f"  Number of unique values: {len(unique_values)}")
    print(f"  Sample values: {list(unique_values[:10])}")

print("\n" + "="*100)
print("SAMPLE ROWS WITH INDEX VALUES:")
print("="*100)

# Reset index to see all the index columns as regular columns
data_with_index = data.reset_index()
print(f"\nColumns after resetting index: {data_with_index.columns.tolist()}")

print("\n" + "="*100)
print("First 20 rows showing ALL columns including index/feature information:")
print("="*100)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)

print(data_with_index.head(20))

# Save this expanded version to CSV
csv_with_features = pkl_path.replace('.pkl', '_with_features.csv')
data_with_index.to_csv(csv_with_features, index=False)
print(f"\n[SUCCESS] Full data with feature information saved to: {csv_with_features}")

# Show unique feature groups
print("\n" + "="*100)
print("UNIQUE FEATURE GROUPS:")
print("="*100)
if 'feature group' in data_with_index.columns:
    print(data_with_index['feature group'].unique())
