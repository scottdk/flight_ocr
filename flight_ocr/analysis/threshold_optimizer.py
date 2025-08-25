"""
Threshold Optimization Module for Flight OCR

This module provides functionality to optimize OCR preprocessing thresholds
for better text extraction results. It focuses purely on analysis logic
while delegating image processing and multithreading to the image_processor module.

Key Features:
- Backend-agnostic threshold analysis
- Flexible threshold specification parsing
- Rich colored output with progress tracking
- Clean separation from OCR implementation details

Dependencies:
- Required: pathlib, argparse, os, sys, datetime
- Optional: pandas, rich (for enhanced display)
- Core modules: flight_ocr.core.image_processor for all OCR operations
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
    
# Add the project root to Python path only when running directly (not with -m)
if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from rich import print as rprint
    from rich.console import Console
    from rich.table import Table
except ImportError as e:
    print(f"Warning: Missing optional dependency: {e}")
    pd = None
    plt = None
    rprint = print
    Console = None
    Table = None

# Import from the new package structure
from flight_ocr.utils.cleaning import clean_lines
from flight_ocr.core.image_processor import batch_process_images_for_ocr, process_image_for_ocr

def estimate_optimal_workers():
    """
    Estimate the optimal number of worker processes based on CPU cores.
    
    OCR processing is typically CPU-intensive, so we use a conservative approach:
    - For 1-2 cores: Use 1 worker
    - For 3-4 cores: Use 2-3 workers (leave 1 core for system)
    - For 5-8 cores: Use 75% of cores
    - For 9+ cores: Use 75% of cores with a reasonable maximum
    
    Returns:
        int: Recommended number of workers
    """
    try:
        cpu_count = os.cpu_count()
        if cpu_count is None:
            return 2  # Safe fallback
        
        if cpu_count <= 2:
            return 1
        elif cpu_count <= 4:
            return min(cpu_count - 1, 3)  # Leave 1 core free, max 3
        elif cpu_count <= 8:
            return int(cpu_count * 0.75)  # Use 75% of cores
        else:
            return min(int(cpu_count * 0.75), 12)  # Cap at 12 workers for very high core counts
    except:
        return 2  # Safe fallback on any error

def parse_threshold_values(threshold_param):
    """
    Parse threshold parameter that can accept single values, lists, or ranges.
    
    Args:
        threshold_param (str or int): Threshold specification
            - Single value: 171 or "171"
            - Range: "171-173"
            - List: "171,173" 
            - Mixed: "171,175,177-179,180"
    
    Returns:
        list: List of threshold values as integers
    
    Examples:
        >>> parse_threshold_values("171")
        [171]
        >>> parse_threshold_values("171-173")
        [171, 172, 173]
        >>> parse_threshold_values("171,173")
        [171, 173]
        >>> parse_threshold_values("171,175,177-179,180")
        [171, 175, 177, 178, 179, 180]
    """
    if isinstance(threshold_param, int):
        return [threshold_param]
    
    threshold_str = str(threshold_param)
    thresholds = []
    
    # Split by commas to handle lists
    parts = [part.strip() for part in threshold_str.split(',')]
    
    for part in parts:
        if '-' in part and not part.startswith('-'):
            # Handle range (e.g., "171-173")
            try:
                start, end = part.split('-', 1)
                start_val = int(start.strip())
                end_val = int(end.strip())
                thresholds.extend(range(start_val, end_val + 1))
            except ValueError:
                raise ValueError(f"Invalid range format: {part}")
        else:
            # Handle single value
            try:
                thresholds.append(int(part))
            except ValueError:
                raise ValueError(f"Invalid threshold value: {part}")
    
    # Remove duplicates and sort
    return sorted(list(set(thresholds)))

def _analyze_ocr_text(lines, image_path, threshold, skip, take):
    """
    Analyze OCR text to identify issues and create analysis DataFrame.
    
    This function processes the cleaned OCR lines and flags lines 
    that don't match expected patterns for flight data.
    
    Args:
        lines: List of cleaned OCR text lines
        image_path: Path to the processed image
        threshold: Threshold value used for processing
        skip: Number of rows to skip
        take: Number of rows to take
        
    Returns:
        tuple: (issue_count, DataFrame) containing issue count and complete analysis results
    """
    import re
    
    if not lines:
        # Empty OCR result
        return 0, None
    
    # Clean lines (they should already be cleaned but ensure we have price pattern)
    lines, price_pattern = clean_lines(lines)
    
    # Define patterns for valid flight data
    price_pattern = re.compile(r'^\$\d{1,3}(?:,\d{3})*,?$')  # Allow trailing comma
    day_pattern = re.compile(r'^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)$', re.IGNORECASE)
    date_pattern = re.compile(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d{1,2}$', re.IGNORECASE)
    
    # Number lines and apply skip/take logic
    numbered_lines = list(enumerate(lines, start=1))
    if skip == 0:
        lines_to_check = numbered_lines
    else:
        lines_to_check = numbered_lines[skip:skip+take] if take > 0 else numbered_lines[skip:]
        
    # Create DataFrame with all lines and flag truly problematic lines as issues
    all_data = []
    issue_count = 0
    
    for num, line in lines_to_check:
        line_clean = line.strip()
        
        # Check if line matches any valid pattern
        is_price = price_pattern.match(line_clean)
        is_day = day_pattern.match(line_clean)
        is_date = date_pattern.match(line_clean)
        is_valid = is_price or is_day or is_date
        
        # Flag as issue only if it doesn't match any valid pattern
        is_issue = not is_valid
        
        if is_issue:
            issue_count += 1
        
        all_data.append({
            'image': str(image_path),
            'threshold': threshold,
            'skip': skip,
            'take': take,
            'line_number': num,
            'line': line,
            'is_issue': is_issue,
            'is_price': bool(is_price),
            'is_day': bool(is_day),
            'is_date': bool(is_date)
        })
    
    if not all_data:
        return 0, None
        
    if pd is not None:
        df = pd.DataFrame(all_data)
    else:
        df = all_data
    
    return issue_count, df

def to_unix_relative_path(full_path: str) -> str:
    """
    Convert a full path to a workspace-relative, unix-style path.
    Workspace path is fetched from the FLIGHT_OCR_WORKSPACE environment variable,
    or defaults to the current working directory.
    """
    workspace_path = os.getcwd()
    try:
        rel_path = Path(full_path).relative_to(workspace_path)
    except ValueError:
        # If full_path is not under workspace_path, just use the filename
        rel_path = Path(full_path).name
    return str(rel_path).replace("\\", "/")

# Example usage:
# os.environ['FLIGHT_OCR_WORKSPACE'] = r"C:\Users\scott\OneDrive\repos\flight_ocr"
# print(to_unix_relative_path(r"C:\Users\scott\OneDrive\repos\flight_ocr\data\cache\processed_images\flight-2025-08-23 11-34-46_156.png"))
# Output: data/cache/processed_images/flight-2025-08-23 11-34-46_156.png

def batch_process(no_cache=False, max_workers=2, thresholds="171-173", 
                 skip=0, take=9, image_file=None, image_dir=None):
    """
    Process multiple images in batch using the image processor's multithreading.
    
    This function is now threading-agnostic and focuses purely on analysis logic.
    All multithreading is handled by the image_processor module.
    
    Args:
        no_cache: Whether to skip caching (default: False, use cache)
        max_workers: Maximum number of worker processes
        thresholds: Threshold specification (default: "171-173")
            - Single value: 171 or "171"
            - Range: "171-173"
            - List: "171,173" 
            - Mixed: "171,175,177-179,180"
        skip: Number of rows to skip (default: 0)
        take: Number of rows to take (default: 9)
        image_file: Single image file to process (overrides image_dir)
        image_dir: Directory containing images (default: data/input/raw)
    """
    now = datetime.now().strftime('%H:%M:%S')
    
    # Parse threshold values
    try:
        threshold_values = parse_threshold_values(thresholds)
    except ValueError as e:
        rprint(f"[red]❌ Error parsing thresholds: {e}[/red]")
        return

    if not threshold_values:
        rprint(f"[red]❌ No valid threshold values were parsed from: '{thresholds}'. Please provide a valid threshold (e.g., '140-180', '150,160,170').[/red]")
        raise ValueError(f"No valid threshold values parsed from: '{thresholds}'")

    threshold_from = min(threshold_values)
    threshold_to = max(threshold_values)
    
    # Determine images to process
    if image_file:
        # Single image file specified
        image_path = Path(image_file)
        if not image_path.exists():
            rprint(f"[red]❌ Image file not found: {image_file}[/red]")
            return
        images = [image_path]
        rprint(f"[green]📄 Processing single image: {image_file}[/green]")
    else:
        # Use image directory
        images_dir = Path(image_dir) if image_dir else Path("data/input/raw")
        images = sorted([f for f in images_dir.glob("*.png") if not f.name.startswith("_")])
        
        # Check if images were found
        if not images:
            rprint(f"[yellow]⚠️  No PNG images found in {images_dir} directory (excluding files starting with '_')[/yellow]")
            rprint("[cyan]💡 Expected to find images like: flight-*.png, image-*.png, etc.[/cyan]")
            return
        rprint(f"[green]📁 Found {len(images)} images in {images_dir}[/green]")
    
    # Display threshold info
    if len(threshold_values) == 1:
        threshold_display = str(threshold_values[0])
    elif len(threshold_values) <= 5:
        threshold_display = ",".join(map(str, threshold_values))
    else:
        threshold_display = f"{threshold_from}-{threshold_to} ({len(threshold_values)} values)"
    
    total_combinations = len(images) * len(threshold_values)
    rprint(f"[green]📁 Found {len(images)} images to process with thresholds: {threshold_display} "
          f"([bold cyan]{total_combinations}[/bold cyan] total combinations)[/green]")

    # Define progress callback for real-time updates
    start_time = datetime.now()
    def progress_callback(current, total, image_path, threshold):
        """Enhanced progress callback with detailed status and time tracking"""
        nonlocal start_time
        
        if start_time is None:
            start_time = datetime.now()
            
        elapsed = datetime.now() - start_time
        
        # Format elapsed time in human-readable format
        elapsed_seconds = int(elapsed.total_seconds())
        if elapsed_seconds < 60:
            elapsed_str = f"{elapsed_seconds}s"
        elif elapsed_seconds < 3600:  # Less than 1 hour
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            elapsed_str = f"{minutes}m {seconds}s"
        else:  # 1 hour or more
            hours = elapsed_seconds // 3600
            minutes = (elapsed_seconds % 3600) // 60
            seconds = elapsed_seconds % 60
            elapsed_str = f"{hours}h {minutes}m {seconds}s"
        
        if current > 0:
            avg_time_per_task = elapsed.total_seconds() / current
            remaining_tasks = total - current
            eta_seconds = int(avg_time_per_task * remaining_tasks)
            
            # Format ETA in human-readable format
            if eta_seconds < 60:
                eta_str = f"{eta_seconds}s"
            elif eta_seconds < 3600:  # Less than 1 hour
                minutes = eta_seconds // 60
                seconds = eta_seconds % 60
                eta_str = f"{minutes}m {seconds}s"
            else:  # 1 hour or more
                hours = eta_seconds // 3600
                minutes = (eta_seconds % 3600) // 60
                seconds = eta_seconds % 60
                eta_str = f"{hours}h {minutes}m {seconds}s"
        else:
            eta_str = "calculating..."
            
        # Get filename from path for display
        image_name = Path(image_path).name if image_path else "Unknown"
        
        # Create visual progress bar using pipe symbols (green for completed, spaces for remaining)
        bar_width = 20  # Total number of characters in the progress bar
        completed_pipes = int((current / total) * bar_width)
        remaining_spaces = bar_width - completed_pipes
        
        # Use ANSI color codes: green (\033[32m) for completed pipes, spaces for remaining
        green_pipes = '\033[32m' + '|' * completed_pipes + '\033[0m'
        spaces = ' ' * remaining_spaces
        progress_bar = '[' + green_pipes + spaces + ']'
        
        # Show detailed progress with visual bar at the start
        print(f"\r{progress_bar} Elapsed: {elapsed_str} | ETA: {eta_str} | 🔄 [{current}/{total}] {image_name} (th={threshold})", end='', flush=True)
        
        # Add newline on completion
        if current == total:
            print(f"\n✅ Completed all {total} combinations in {elapsed_str}")

    # Use the image processor's batch function for all multithreading
    results = batch_process_images_for_ocr(
        image_paths=images,
        thresholds=threshold_values,
        max_workers=max_workers,
        no_cache=no_cache,
        debug=False,
        progress_callback=progress_callback
    )
    
    # Clear progress line after processing is complete (simplified - nothing to clear now)
    
    # Process results and convert to analysis format
    total_count = 0
    all_results = []
    all_thresholds = []
    dic_cleaned_and_raw_paths = {}

    for i, (image_path, threshold, ocr_text, success, error_msg, cleaned_path, raw_path, processed_path) in enumerate(results, 1):
        if not success:
            rprint(f"[red]❌ Error processing {image_path.name} (threshold={threshold}): {error_msg}[/red]")
            continue
        
        dic_index = (Path(image_path).name, threshold)
        dic_cleaned_and_raw_paths[dic_index] = (to_unix_relative_path(cleaned_path), to_unix_relative_path(raw_path), image_path, to_unix_relative_path(processed_path))

        # Split the OCR text back into lines for analysis
        lines = ocr_text.splitlines() if ocr_text else []
        count, df = _analyze_ocr_text(lines, image_path, threshold, skip, take)
        
        total_count += count
        all_thresholds.append((threshold, count))
        
        if df is not None and not df.empty:
            df['cleaned_path'] = str(cleaned_path) if cleaned_path is not None else None
            df['raw_path'] = str(raw_path) if raw_path is not None else None
            all_results.append(df)
    
    # Ensure we clear any remaining progress line
    import sys
    sys.stdout.write(f"\r{' ' * 120}\r")
    sys.stdout.flush()
        
    # Create analysis tables showing all results (including zero-issue files)
    if all_results and pd is not None:
        rprint(f"\n[bold green]📊 Total issues found (thresholds: {threshold_display}, "
              f"skip={skip}, take={take}): {total_count}[/bold green]")
        
        # Show zero-issue files (perfect candidates) first - moved from end
        zero_issue_files = []
        for threshold, count in all_thresholds:
            if count == 0:
                # Find files with this threshold that had zero issues
                threshold_files = [df for df in all_results if not df.empty and df['threshold'].iloc[0] == threshold]
                for df in threshold_files:
                    if df['is_issue'].sum() == 0:  # No issues in this file
                        zero_issue_files.append((df['image'].iloc[0], threshold))
        
        if zero_issue_files:
            rprint(f"\n[bold green]🏆 Perfect Results (Zero Issues - Best Thresholds):[/bold green]")
            for image_path, threshold in zero_issue_files:
                image_name = Path(image_path).name
                rprint(f"  • [cyan]{image_name}[/cyan] with threshold [yellow]{threshold}[/yellow]")
        
        # Combine all results
        results_df = pd.concat(all_results, ignore_index=True)

        # Show complete results with flagged issues
        rprint("[blue]📋 Complete Results (all lines with issue flags):[/blue]")
        # Only show issue lines for brevity, but mention total count
        # issue_lines = results_df[results_df['is_issue'] == True] if total_count > 0 else pd.DataFrame()
        # if not issue_lines.empty:
        #     print(issue_lines[['image', 'threshold', 'line_number', 'line', 'is_issue']])
        # else:
        #     rprint("[green]✨ All lines match expected price patterns![/green]")

        # # Create thresholds summary
        # thresholds_df = pd.DataFrame(all_thresholds, columns=['threshold', 'count'])
        # thresholds_df = thresholds_df.sort_values(by='threshold')
        # rprint(f"\n[blue]🎯 Thresholds Summary ({len(thresholds_df)} thresholds analyzed):[/blue]")
        # print(thresholds_df)

        # Only show pivot tables if there are issues to analyze
        if total_count > 0:
            # Create a pivot table: count of issues per threshold (totals only)
            # Use all results but count only issues to show zeros for perfect thresholds
            pivot2 = results_df.groupby('threshold')['is_issue'].sum().to_frame('line')
            pivot2.loc['Total'] = pivot2['line'].sum()
            
            # Sort the pivot table by count ascending to find best thresholds
            pivot2_sorted = pivot2.sort_values(by='line', ascending=True)
            
            # Find the minimum count (excluding 'Total') in the sorted pivot table
            min_count = pivot2_sorted.loc[pivot2_sorted.index != 'Total', 'line'].min()
            # Get all thresholds with this minimum count
            lowest_thresholds = pivot2_sorted.loc[(pivot2_sorted['line'] == min_count) & 
                                                 (pivot2_sorted.index != 'Total')].index.tolist()

            # Print the issues for those thresholds FIRST (before Perfect Results)
            _display_issues_for_thresholds(lowest_thresholds, all_results)

            # Now show the pivot tables - include all results to show zeros
            pivot = results_df.groupby(['image', 'threshold'])['is_issue'].sum().unstack(fill_value=0)
            # Add row and column totals
            pivot['Total'] = pivot.sum(axis=1)
            pivot.loc['Total'] = pivot.sum(axis=0)
            
            rprint("\n[bold cyan]📊 Issues Pivot table (count per image/threshold):[/bold cyan]")
            _display_pivot_table(pivot)
            
            # Export pivot table to CSV
            try:
                # Create output directory if it doesn't exist
                output_dir = Path("data/output/results")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create filename with timestamp and threshold info
                rprint(f"[dim]💾 Create filename with timestamp and threshold info[/dim]")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                threshold_str = threshold_display.replace(",", "-").replace(" ", "")
                csv_filename = f"pivot_issues_{timestamp}_{threshold_str}.csv"
                csv_path = output_dir / csv_filename
                
                # Create a copy of pivot with just filenames (not full paths) for CSV export
                pivot_csv = pivot.copy()
                pivot_csv.index = pivot_csv.index.map(lambda x: Path(x).name if x != 'Total' else x)
                
                # Save to CSV
                pivot_csv.to_csv(csv_path)
                rprint(f"[dim]💾 Pivot table saved to: {csv_path}[/dim]")

                # --- Additional: Output filtered pivot with only columns containing at least one zero ---
                try:
                    
                    filtered_csv_path = csv_path.parent / (csv_path.stem + '_zeros_only.csv')
                    rprint(f"[dim]💾 Creating Zeros Only CSV: {filtered_csv_path}[/dim]")
                    # Remove 'Total' row and column if present
                    pivot_data = pivot_csv.copy()
                    if pivot_data.index[-1] == 'Total':
                        pivot_data = pivot_data.iloc[:-1, :]
                    if 'Total' in pivot_data.columns:
                        pivot_data = pivot_data.drop(columns=['Total'])

                    filtered = pivot_data.copy()
                    
                    # # Identify columns (thresholds) with at least one zero (ignoring 'image' column)
                    data_cols = [col for col in filtered.columns if col != 'image']
                    # zero_cols = [col for col in data_cols if (filtered[col] == 0).any()]

                    # # Always keep 'image' column at the start if present
                    # if 'image' in filtered.columns:
                    #     cols_to_keep = ['image'] + zero_cols
                    # else:
                    #     cols_to_keep = zero_cols

                    # Compute Zero_Count for each column (excluding 'image')
                    zero_count = {col: (filtered[col] == 0).sum() for col in data_cols}

                    # Sort columns (except 'image') by Zero_Count descending (reverse order)
                    if data_cols:
                        sorted_zero_cols = sorted(data_cols, key=lambda c: zero_count[c], reverse=True)
                    else:
                        sorted_zero_cols = []
                    if 'image' in filtered.columns:
                        sorted_cols = ['image'] + sorted_zero_cols
                    else:
                        sorted_cols = sorted_zero_cols
                    filtered = filtered[sorted_cols]

                    # Add total_zeros column after image column (count zeros in each row, excluding 'image' and Zero_Count row)
                    if data_cols:
                        if 'image' in filtered.columns:
                            # Exclude the Zero_Count row for now
                            data_part = filtered.iloc[:-1] if filtered.index[-1] == 'Zero_Count' else filtered
                            zero_count_per_row = data_part[sorted_zero_cols].apply(lambda row: (row == 0).sum(), axis=1)
                            filtered.insert(1, 't0', list(zero_count_per_row) + ([None] if filtered.index[-1] == 'Zero_Count' else []))
                        else:
                            data_part = filtered.iloc[:-1] if filtered.index[-1] == 'Zero_Count' else filtered
                            zero_count_per_row = data_part[sorted_zero_cols].apply(lambda row: (row == 0).sum(), axis=1)
                            filtered.insert(0, 't0', list(zero_count_per_row) + ([None] if filtered.index[-1] == 'Zero_Count' else []))

                        # Add Zero_Count row at the bottom, matching column count
                        if 'image' in filtered.columns:
                            zero_count_row = ['Zero_Count', sum(zero_count.values())] + [zero_count[col] for col in sorted_zero_cols]
                            filtered.loc['Zero_Count'] = zero_count_row
                        else:
                            zero_count_row = [sum(zero_count.values())] + [zero_count[col] for col in sorted_zero_cols]
                            filtered.loc['Zero_Count'] = zero_count_row
                    else:
                        # If no data_cols, output a minimal CSV with just image and t0 columns and a Zero_Count row of zeros
                        if 'image' in pivot_data.columns:
                            filtered = pivot_data[['image']].copy()
                            filtered['t0'] = 0
                            filtered.loc['Zero_Count'] = ['Zero_Count', 0]
                        else:
                            filtered = pd.DataFrame({'t0': [0]*len(pivot_data)})
                            filtered.loc['Zero_Count'] = [0]

                    # Fix: Ensure all integer columns have only int values (no None/NaN) except for the Zero_Count row, which will have an empty string
                    int_cols = [col for col in filtered.columns if col != 'image']
                    if filtered.index[-1] == 'Zero_Count':
                        # Restore correct Zero_Count values for threshold columns and t0
                        for col in int_cols:
                            if col == 't0':
                                # t0 for Zero_Count row is the sum of zero_count.values()
                                filtered.at['Zero_Count', col] = sum(zero_count.values()) if zero_count else 0
                            else:
                                filtered.at['Zero_Count', col] = int(zero_count.get(col, 0))
                        # For all other rows, ensure int type and no NaN/None
                        for col in int_cols:
                            filtered.loc[filtered.index != 'Zero_Count', col] = filtered.loc[filtered.index != 'Zero_Count', col].apply(lambda x: int(float(x)) if pd.notnull(x) and x != '' else 0)
                    else:
                        for col in int_cols:
                            filtered[col] = filtered[col].apply(lambda x: int(float(x)) if pd.notnull(x) and x != '' else 0)
                    # Cast DataFrame to object dtype to ensure ints are written as plain ints in CSV
                    filtered = filtered.astype(object)

                    # Sort rows vertically by t0 (excluding Zero_Count row)
                    if 'image' in filtered.columns:
                        data_rows = filtered.iloc[:-1] if filtered.index[-1] == 'Zero_Count' else filtered
                        data_rows_sorted = data_rows.sort_values(by='t0', ascending=True)
                        filtered = pd.concat([data_rows_sorted, filtered.iloc[[-1]]]) if filtered.index[-1] == 'Zero_Count' else data_rows_sorted
                    else:
                        data_rows = filtered.iloc[:-1] if filtered.index[-1] == 'Zero_Count' else filtered
                        data_rows_sorted = data_rows.sort_values(by='t0', ascending=True)
                        filtered = pd.concat([data_rows_sorted, filtered.iloc[[-1]]]) if filtered.index[-1] == 'Zero_Count' else data_rows_sorted

                    # Save to new CSV (always write, even if data_cols is empty)
                    filtered_csv_path = csv_path.parent / (csv_path.stem + '_zeros_only.csv')
                    if 'image' in filtered.columns:
                        filtered.to_csv(filtered_csv_path, index=False)
                    else:
                        filtered.to_csv(filtered_csv_path, index=True)
                    rprint(f"[dim]💾 Filtered (zeros only) pivot table saved to: {filtered_csv_path}[/dim]")
                    print(filtered_csv_path)
                    print(filtered)
                    
                    
                    # --- Additional: Output optimal_thresholds.csv ---
                    try:
                        # Only proceed if there are threshold columns (data_cols)
                        if data_cols and sorted_zero_cols:
                            optimal_rows = []
                            # Use the same sorted_zero_cols order as in zeros_only
                            for idx, row in filtered.iterrows():
                                if idx == 'Zero_Count':
                                    continue
                                image_val = row['image'] if 'image' in filtered.columns else idx
                                # Find the first threshold column (from left to right) with a zero
                                found = False
                                for th in sorted_zero_cols:
                                    if row[th] == 0:
                                        chosen_th = th
                                        chosen_val = 0
                                        found = True
                                        break
                                if not found:
                                    # No zero found, so find the threshold with the lowest value for this image in filtered
                                    threshold_cols = [col for col in sorted_zero_cols if col not in ('image', 't0')]
                                    if threshold_cols:
                                        min_val = min([row[th] for th in threshold_cols])
                                        min_thresholds = [th for th in threshold_cols if row[th] == min_val]
                                        chosen_th = min_thresholds[0] if min_thresholds else None
                                        chosen_val = min_val
                                    else:
                                        chosen_th = None
                                        chosen_val = None

                                # Set image_val to the cleaned CSV path for this image and threshold
                                # Format: data/output/cleaned/th_{threshold:03d}{image_basename}_cleaned.csv
                                if image_val: 
                                    if chosen_th is None:
                                        chosen_th='000'    
                                    image_basename = Path(image_val).stem
                                    cleaned_csv_name = f"th{int(chosen_th):03d}_{image_basename}_cleaned.csv"
                                    cleaned_csv_path = str(Path("data/output/cleaned") / cleaned_csv_name)
                                    image_val = cleaned_csv_path
                                cleaned_path = dic_cleaned_and_raw_paths.get((idx, int(chosen_th)), (None, None))[0]
                                raw_path = dic_cleaned_and_raw_paths.get((idx, int(chosen_th)), (None, None))[1]
                                image_full_path = dic_cleaned_and_raw_paths.get((idx, int(chosen_th)), (None, None, None))[2]
                                processed_path = dic_cleaned_and_raw_paths.get((idx, int(chosen_th)), (None, None, None, None))[3]
                                optimal_rows.append([idx, chosen_th, chosen_val, cleaned_path, raw_path, image_full_path, processed_path])

                            # Write to CSV
                            # optimal_csv_path = filtered_csv_path.parent / 'optimal_thresholds.csv'
                            optimal_csv_path = csv_path.parent / (csv_path.stem + '_optimal_thresholds.csv')
                            import csv
                            with open(optimal_csv_path, 'w', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(['image', 'threshold', 'value_used', 'clean_data', 'raw_data', 'original_image', 'processed_image'])
                                writer.writerows(optimal_rows)
                                
                                
                            rprint(f"[dim]💾 Optimal thresholds saved to: {optimal_csv_path}[/dim]")
                            # Also copy to 'optimal_thresholds.csv' in the same folder (overwrite if exists)
                            import shutil
                            generic_csv_path = optimal_csv_path.parent / 'optimal_thresholds.csv'
                            shutil.copyfile(optimal_csv_path, generic_csv_path)
                            rprint(f"[dim]💾 Also copied to: {generic_csv_path}[/dim]")
                    except Exception as e:
                        rprint(f"[yellow]⚠️  Could not save optimal_thresholds.csv: {e}[/yellow]")
                except Exception as e:
                    rprint(f"[yellow]⚠️  Could not save filtered (zeros only) pivot table: {e}[/yellow]")

                # --- End additional ---
                
            except Exception as e:
                rprint(f"[yellow]⚠️  Could not save pivot table to CSV: {e}[/yellow]")
            
            rprint("\n[bold magenta]📈 Issues by Threshold:[/bold magenta]")
            _display_threshold_table(pivot2)
            
            rprint("\n[bold yellow]🏆 Issues by Threshold (sorted by count ascending):[/bold yellow]")
            _display_threshold_table(pivot2_sorted)
            
            # Display chart if available
            # _display_chart(pivot2)  # Commented out temporarily
            
            # Show optimal threshold identification at the end
            rprint(f"\n[bold green]🎯 Threshold(s) with the lowest issue count ({min_count}): {lowest_thresholds}[/bold green]")

    elif all_results:
        rprint("[yellow]⚠️  pandas not available - cannot create detailed pivot tables[/yellow]")
        
    # Display summary
    rprint(f"\n[bold cyan]📋 Total issues found (thresholds: {threshold_display}, skip={skip}, take={take}): {total_count}[/bold cyan]")


def _display_pivot_table(pivot):
    """Display pivot table using rich if available, otherwise fallback to print."""
    if Console is None or Table is None:
        rprint(pivot)
        return
        
    try:
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("image", style="bold")
        col_colors = ["cyan", "green", "magenta", "blue", "red", 
                      "bright_cyan", "bright_green", "bright_magenta", "bright_blue", "bright_red"]
        
        for i, col in enumerate(pivot.columns):
            style = col_colors[i % len(col_colors)]
            table.add_column(str(col), style=style)
            
        # Add all rows except the 'Total' row
        for idx, row in pivot.iterrows():
            if str(idx) != 'Total':
                table.add_row(str(idx), *[str(val) for val in row.values])
                
        # Add the 'Total' row as a yellow bold footer if present
        if 'Total' in pivot.index:
            total_row = pivot.loc['Total']
            table.add_row(
                '[b yellow]Total[/b yellow]',
                *[f'[b yellow]{val}[/b yellow]' for val in total_row.values],
                end_section=True
            )
        console.print(table)
    except (ImportError, RuntimeError) as e:
        rprint(f"[orange3]⚠️  Error displaying table: {e}[/orange3]")
        rprint(pivot)


def _display_threshold_table(pivot2):
    """Display threshold pivot table using rich if available."""
    if Console is None or Table is None:
        rprint(pivot2)
        return
        
    try:
        console = Console()
        table2 = Table(show_header=True, header_style="bold magenta")
        table2.add_column("threshold", style="bold")
        table2.add_column("count", style="cyan")
        
        for idx, row in pivot2.iterrows():
            if str(idx) != 'Total':
                table2.add_row(str(idx), str(row['line']))
                
        if 'Total' in pivot2.index:
            total_row = pivot2.loc['Total']
            table2.add_row(
                '[b yellow]Total[/b yellow]',
                f'[b yellow]{total_row["line"]}[/b yellow]',
                end_section=True
            )
        console.print(table2)
    except (ImportError, RuntimeError) as e:
        rprint(f"[orange3]⚠️  Error displaying threshold table: {e}[/orange3]")
        rprint(pivot2)


def _display_issues_for_thresholds(lowest_thresholds, all_results):
    """Display issues for the lowest thresholds."""
    for threshold in lowest_thresholds:
        rprint(f"\n[bold magenta]Issues for threshold {threshold}:[/bold magenta]")
        for df in all_results:
            # Filter to only show lines with issues for this threshold
            issue_data = df[(df['threshold'] == threshold) & (df['is_issue'] == True)]
            if not issue_data.empty:
                rprint(f"[bold cyan]{issue_data['image'].iloc[0]}[/bold cyan]")
                for _, row in issue_data.iterrows():
                    line_number = row['line_number']
                    line_content = row['line']
                    rprint(f"[bold yellow]{line_number}:[/bold yellow] {line_content}")


def _display_chart(pivot2):
    """Display bar chart if matplotlib is available."""
    if plt is None:
        rprint("[yellow]⚠️  matplotlib not available - cannot display chart[/yellow]")
        return
        
    try:
        rprint("[green]📊 Displaying threshold analysis chart...[/green]")
        _, ax = plt.subplots(figsize=(8, 4))
        pivot2_no_total = pivot2.drop('Total', errors='ignore')
        pivot2_no_total['line'].plot(kind='bar', ax=ax, color='skyblue')
        ax.set_title('Count of Issues per Threshold')
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Count')
        plt.tight_layout()
        plt.show()
    except (ImportError, RuntimeError) as e:
        rprint(f"[red]❌ Error displaying chart: {e}[/red]")


if __name__ == "__main__":
    # Get optimal worker recommendation
    recommended_workers = estimate_optimal_workers()
    
    main_parser = argparse.ArgumentParser(description="Optimize OCR thresholds for flight image processing")
    main_parser.add_argument('--no-cache', action='store_true', dest='no_cache',
                            help='Skip cache, perform OCR, and update cache with new results (default: use cache if available)')
    main_parser.add_argument('--max-workers', type=int, default=recommended_workers, 
                            help=f'Maximum number of worker processes (default: {recommended_workers} - auto-detected based on {os.cpu_count()} CPU cores)')
    main_parser.add_argument('--thresholds', type=str, default='171-173',
                            help='Threshold values: single (171), range (171-173), list (171,173), or mixed (171,175,177-179) (default: 171-173)')
    main_parser.add_argument('--skip', type=int, default=0,
                            help='Number of rows to skip (default: 0)')
    main_parser.add_argument('--take', type=int, default=9,
                            help='Number of rows to take (default: 9)')
    main_parser.add_argument('--image-file', type=str,
                            help='Single image file to process (overrides --image-dir)')
    main_parser.add_argument('--image-dir', type=str, default='data/input/raw',
                            help='Directory containing images (default: data/input/raw)')
    main_parser.add_argument('--check-ocr', action='store_true',
                            help='Check OCR backend installation and exit')
    main_parser.set_defaults(max_workers=recommended_workers)
    main_args = main_parser.parse_args()
    
    # Handle --check-ocr option
    if main_args.check_ocr:
        rprint("[bold cyan]🔍 OCR Backend Installation Check[/bold cyan]")
        rprint("[yellow]⚠️  OCR backend checks have been moved to the processing layer.[/yellow]")
        rprint("[cyan]💡 The threshold optimizer is now backend-agnostic and doesn't directly check OCR engines.[/cyan]")
        rprint("[green]✅ Try processing an image to see if OCR is working properly.[/green]")
        exit(0)
    
    # Display worker recommendation if using default
    cpu_cores = os.cpu_count()
    if main_args.max_workers == recommended_workers:
        rprint(f"[dim]💻 Auto-detected {cpu_cores} CPU cores, using {main_args.max_workers} workers (recommended)[/dim]")
    else:
        rprint(f"[dim]💻 Detected {cpu_cores} CPU cores, using {main_args.max_workers} workers (recommended: {recommended_workers})[/dim]")
    
    batch_process(
        no_cache=main_args.no_cache, 
        max_workers=main_args.max_workers,
        thresholds=main_args.thresholds,
        skip=main_args.skip,
        take=main_args.take,
        image_file=main_args.image_file,
        image_dir=main_args.image_dir
    )


class ThresholdOptimizer:
    """
    Wrapper class for threshold optimization functionality.
    
    This class provides a clean interface to the threshold optimization
    functions for use in other parts of the application.
    """
    
    @staticmethod
    def optimize_thresholds(no_cache=False, max_workers=4, thresholds="171-173",
                          skip=0, take=9, image_file=None, image_dir=None):
        """
        Run threshold optimization analysis.
        
        Args:
            no_cache: Whether to skip caching for OCR processing
            max_workers: Maximum number of worker processes for parallel processing
            thresholds: Threshold values specification (default: "171-173")
                - Single value: 171 or "171"
                - Range: "171-173"
                - List: "171,173" 
                - Mixed: "171,175,177-179,180"
            skip: Number of rows to skip (default: 0)
            take: Number of rows to take (default: 9)
            image_file: Single image file to process (overrides image_dir)
            image_dir: Directory containing images (default: data/input/raw)
        """
        return batch_process(
            no_cache=no_cache, 
            max_workers=max_workers,
            thresholds=thresholds,
            skip=skip,
            take=take,
            image_file=image_file,
            image_dir=image_dir
        )
    