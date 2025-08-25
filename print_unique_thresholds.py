# Script to print unique threshold values (no spaces) from a hardcoded CSV file
import csv
import glob
import os

def find_latest_optimal_thresholds_csv(folder):
    pattern = os.path.join(folder, "pivot_issues*_optimal_thresholds.csv")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No pivot_issues*_optimal_thresholds.csv files found.")
    latest = max(files, key=os.path.getmtime)
    return latest

def print_unique_thresholds(csv_path):
    thresholds = set()
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            thresholds.add(row['threshold'])
    print(",".join(sorted(thresholds, key=int)))

if __name__ == "__main__":
    folder = "data/output/results"
    latest_csv = find_latest_optimal_thresholds_csv(folder)
    print_unique_thresholds(latest_csv)
