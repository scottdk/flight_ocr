# This script filters a pivot_issues CSV to only include columns (thresholds) with at least one zero value, adds a Zero_Count row, and sorts columns by Zero_Count ascending.
import pandas as pd
import sys
from pathlib import Path

# Input and output paths
input_csv = "data/output/results/pivot_issues_20250825_110257_100-200(101values).csv"
output_csv = "data/output/results/pivot_issues_20250825_110257_100-200(101values)_zeros_only.csv"

df = pd.read_csv(input_csv)

# Remove 'Total' row if present
if df.iloc[-1,0] == 'Total':
    df_data = df.iloc[:-1].copy()
    total_row = df.iloc[-1]
else:
    df_data = df.copy()

# Identify columns (thresholds) with at least one zero (excluding 'image' column)
zero_cols = [col for col in df_data.columns if col != 'image' and (df_data[col] == 0).any()]

# Always keep 'image' column at the start
cols_to_keep = ['image'] + zero_cols
filtered = df_data[cols_to_keep].copy()

# Compute Zero_Count for each column (excluding 'image')
zero_count = {col: (filtered[col] == 0).sum() for col in zero_cols}

# Add Zero_Count row at the bottom
zero_count_row = ['Zero_Count'] + [zero_count[col] for col in zero_cols]
filtered.loc[len(filtered)] = zero_count_row

# Sort columns (except 'image') by Zero_Count ascending
sorted_cols = ['image'] + sorted(zero_cols, key=lambda c: zero_count[c])
filtered = filtered[sorted_cols]

# Save to new CSV
filtered.to_csv(output_csv, index=False)
print(f"Filtered CSV with zeros only saved to: {output_csv}")
