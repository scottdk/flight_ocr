import pandas as pd
from pathlib import Path

# Load the original pivot CSV
csv_path = Path("data/output/results/pivot_issues_20250825_111945_157-158-159-160-161.csv")
df = pd.read_csv(csv_path)

# Remove the Total row and column for processing
core = df.loc[df['image'] != 'Total'].copy()
core = core.drop(columns=['Total'])

# Identify columns (thresholds) with at least one zero (ignore 'image')
zero_cols = [col for col in core.columns if col != 'image' and (core[col] == 0).any()]

# Filter to only those columns, always keep 'image'
filtered = core[['image'] + zero_cols].copy()

# Compute Zero_Count for each threshold column
zero_count = {col: (filtered[col] == 0).sum() for col in zero_cols}
zero_count_row = ['Zero_Count'] + [zero_count[col] for col in zero_cols]

# Sort columns (except 'image') by Zero_Count ascending
sorted_cols = ['image'] + sorted(zero_cols, key=lambda c: zero_count[c])
filtered = filtered[sorted_cols]

# Add Zero_Count row at the bottom
filtered.loc[len(filtered)] = zero_count_row

# Save to new CSV
out_path = csv_path.parent / (csv_path.stem + '_zeros_only.csv')
filtered.to_csv(out_path, index=False)
print(f"Saved: {out_path}")
