import pandas as pd

input_file = "off-target.bz2"

try:
    # 1. Use pandas.read_pickle to load the compressed object directly
    df = pd.read_pickle(input_file, compression='bz2')

    # Set pandas display options to show all columns in table format
    pd.set_option('display.max_columns', None)     # Show all columns
    pd.set_option('display.max_rows', None)        # Show all rows
    pd.set_option('display.width', 1000)           # Wide display
    pd.set_option('display.max_colwidth', 25)      # Column width
    pd.set_option('display.expand_frame_repr', False)  # Don't wrap to multiple lines

    print("="*150)
    print("TIGER Data Preview: First 10 Rows × All 28 Columns")
    print(f"Total Dataset: {len(df):,} rows × {len(df.columns)} columns")
    print("="*150)
    print()

    # 2. Print the first 10 rows with all columns in table format
    print(df.head(10).to_string(index=True))

    print("\n" + "="*150)
    print("Column Information")
    print("="*150)

    # 3. Print column details in a nice table
    col_info = pd.DataFrame({
        'Column Name': df.columns,
        'Data Type': df.dtypes.values,
        'Non-Null Count': [df[col].count() for col in df.columns],
        'Sample Value': [str(df[col].iloc[0])[:30] for col in df.columns]
    })
    col_info.index = range(1, len(col_info) + 1)
    print(col_info.to_string())

    # 4. Export to CSV for easier viewing (optional)
    output_file = "data_preview_10rows.csv"
    df.head(10).to_csv(output_file, index=False)
    print(f"\n✓ First 10 rows exported to: {output_file}")
    print("  (You can open this in Excel or any spreadsheet program)")

except ImportError:
    print("Error: The 'pandas' library is not installed.")
    print("Please install it using: pip install pandas")
except Exception as e:
    print(f"An error occurred while loading the DataFrame: {e}")