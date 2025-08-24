"""
Threshold Optimization Module for Flight OCR

This module provides functionality to optimize OCR preprocessing thresholds
for better text extraction results. It includes batch processing capabilities
with multiprocessing support and visualization of results.

Key Features:
- Image preprocessing with configurable thresholds
- OCR text extraction and cleaning
- Batch processing with caching support
- Result visualization with tables and charts
- Multiprocessing for efficient threshold testing

Dependencies:
- Required: pathlib, argparse, os, sys, datetime, functools
- Optional: pandas, matplotlib, rich (for enhanced display)
- Core modules: flight_ocr.utils, flight_ocr.core
"""
import argparse
import concurrent.futures
import os
import pickle
import sys
from datetime import datetime
from functools import partial
from pathlib import Path

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
from flight_ocr.utils.cache import get_cache_file, load_from_cache, save_to_cache
from flight_ocr.utils.cleaning import clean_lines
from flight_ocr.core.image_processor import preprocess_image, run_ocr

def process_image(threshold=None, skip=None, take=None):
    """
    Process a single image with OCR preprocessing and extraction.
    
    Args:
        threshold: Binarization threshold (default from args)
        skip: Number of rows to skip (default from args) 
        take: Number of rows to take (default from args)
        
    Returns:
        tuple: (count, DataFrame) containing count of filtered lines and DataFrame with results
    """
    parser = argparse.ArgumentParser(description="Test OCR preprocessing and extraction.")
    parser.add_argument('image', nargs='?', default='images/Screenshot from 2025-08-23 10-24-54.png',
                        help='Path to the image file to test (default: images/Screenshot from 2025-08-23 10-24-12.png)')
    parser.add_argument('--tess-config', type=str, 
                        default="-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–— --psm 6 --oem 3", 
                        help='Tesseract config string')
    parser.add_argument('--threshold', type=int, default=170, help='Threshold for binarization (default: 170)')
    parser.add_argument('--skip', type=int, default=0, help='number of rows to skip (default: 0)')
    parser.add_argument('--take', type=int, default=0, help='number of rows to take (default: 0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    parsed_args = parser.parse_args()

    threshold_val = threshold if threshold is not None else parsed_args.threshold
    image_path = Path(parsed_args.image)

    # Raw OCR cache path
    raw_cache_dir = image_path.parent / ".raw_cache"
    raw_cache_dir.mkdir(exist_ok=True)
    raw_cache_file = raw_cache_dir / (image_path.stem + f"_{threshold_val}.pkl")

    if raw_cache_file.exists():
        with open(raw_cache_file, "rb") as f:
            ocr_text = pickle.load(f)
        print(f"Loaded OCR text from cache. img={image_path}, threshold={threshold_val} ")
    else:
        print(f"Preprocessing image. img={image_path}, threshold={threshold_val} ")
        img_bin = preprocess_image(image_path, debug=parsed_args.debug, threshold=threshold_val)
        # Save preprocessed image with _ prefix
        processed_dir = image_path.parent / "processed"
        processed_dir.mkdir(exist_ok=True)
        preprocessed_path = processed_dir / (image_path.stem + f"_{threshold_val}" + image_path.suffix)
        img_bin.save(preprocessed_path)
        print(f"run_ocr. img={image_path}, threshold={threshold_val} ")
        ocr_text = run_ocr(img_bin, debug=parsed_args.debug, tess_config=parsed_args.tess_config)
        with open(raw_cache_file, "wb") as f:
            pickle.dump(ocr_text, f)
    
    # Save raw OCR text to CSV in raw_ocr_text folder
    raw_ocr_dir = image_path.parent / "raw_ocr_text"
    raw_ocr_dir.mkdir(exist_ok=True)
    raw_ocr_csv = raw_ocr_dir / f"th{threshold_val}_{image_path.stem}_raw.csv"

    print(f"Saving raw OCR text to CSV. img={image_path}, threshold={threshold_val}, csv={raw_ocr_csv}")
    
    # Save the raw OCR text to a CSV file
    if pd is not None:
        pd.DataFrame({'ocr_text': [ocr_text]}).to_csv(raw_ocr_csv, index=False)

    lines = ocr_text.replace('\n\n', '\n').splitlines()
    lines, price_pattern = clean_lines(lines)
    
    numbered_lines = list(enumerate(lines, start=1))
    skip_val = skip if skip is not None else parsed_args.skip
    take_val = take if take is not None else parsed_args.take
    
    if skip_val == 0:
        lines_to_check = numbered_lines
    else:
        lines_to_check = numbered_lines[skip_val:skip_val+take_val]
        
    filtered = [(num, line) for num, line in lines_to_check if not price_pattern.match(line.strip())]
    
    if pd is None:
        return 0, None
        
    if all(line[1].strip()[:3].isalpha() for line in filtered):
        count = 0
        df = pd.DataFrame()
    else:
        filtered = [(num, line) for num, line in filtered if not line.strip()[:3].isalnum()]
        count = sum(1 for _, line in filtered if not line.strip()[:3].isalpha())
        df = pd.DataFrame({
            'image': [str(image_path)] * len(filtered),
            'threshold': [threshold_val] * len(filtered),
            'skip': [skip_val] * len(filtered),
            'take': [take_val] * len(filtered),
            'line_number': [num for num, _ in filtered],
            'line': [line for _, line in filtered]
        })
    return count, df

# Top-level process_wrapper for multiprocessing
def process_wrapper(task_args, refresh_cache=False):
    """
    Wrapper function for multiprocessing to handle image processing tasks.
    
    Args:
        task_args: Tuple of (image_path, threshold, skip, take)
        refresh_cache: Whether to refresh the cache
        
    Returns:
        tuple: (count, DataFrame, used_cache_flag)
    """
    image_path, threshold, skip, take = task_args
    cache_file = get_cache_file(image_path, threshold)
    
    used_cache = False
    now = datetime.now().strftime('%H:%M:%S')
    
    if not refresh_cache and os.path.exists(cache_file):
        loaded = load_from_cache(cache_file)
        # Only use cache if it is a tuple of length 2 (old cache format)
        if isinstance(loaded, tuple) and len(loaded) == 2:
            count, df = loaded
            used_cache = True
            # Save df to a CSV file with threshold and image_path in the filename
            if df is not None and not df.empty:
                results_dir = "results"
                os.makedirs(results_dir, exist_ok=True)
                csv_filename = f"th{threshold}_{Path(image_path).stem}.csv"
                csv_path = os.path.join(results_dir, csv_filename)
                df.to_csv(csv_path, index=False)

            # Clean the 'line' values as specified, then recount
            if df is not None and not df.empty and 'line' in df.columns:
                lines, price_pattern = clean_lines(df['line'].astype(str).tolist())
                # Filter out lines matching price_pattern
                filtered = [(num, line) for num, line in zip(df['line_number'], lines) 
                           if not price_pattern.match(line.strip())]
                df = df[df['line_number'].isin([num for num, _ in filtered])].reset_index(drop=True)
                lines = df['line'].astype(str).tolist()
                # Recount as in process_image
                filtered2 = [(num, line) for num, line in zip(df['line_number'], lines) 
                            if not line.strip()[:3].isalpha()]
                count = len(filtered2)
                if filtered2:
                    df = df[df['line_number'].isin([num for num, _ in filtered2])].reset_index(drop=True)
                else:
                    df = df.iloc[0:0]  # empty DataFrame with same columns
            return count, df, used_cache
        # Otherwise, fall through to recompute below

    # Recompute and write to cache
    try:
        rprint(f"[bold yellow][{now}][Worker {os.getpid()}] recomputing and writing to cache: [magenta]{cache_file}[/magenta][/bold yellow]")
        sys.argv = [sys.argv[0], str(image_path), '--threshold', str(threshold), '--skip', str(skip), '--take', str(take)]
        count, df = process_image(threshold=threshold, skip=skip, take=take)
        save_to_cache(cache_file, (count, df))
        used_cache = False
        return count, df, used_cache
    except (ImportError, FileNotFoundError, ValueError) as exc:
        # Always return a tuple, even on error
        print(f"Error processing {image_path}: {exc}")
        return 0, None, False

def batch_process(refresh_cache=False, max_workers=2):
    """
    Process multiple images in batch using multiprocessing.
    
    Args:
        refresh_cache: Whether to refresh the cache
        max_workers: Maximum number of worker processes
    """
    now = datetime.now().strftime('%H:%M:%S')
    images_dir = Path("data/input/raw")
    images = sorted([f for f in images_dir.glob("*.png") if not f.name.startswith("_")])
    threshold_from = 171
    threshold_to = 173
    skip = 0
    take = 9
    
    # Check if images were found
    if not images:
        rprint(f"[yellow]⚠️  No PNG images found in {images_dir} directory (excluding files starting with '_')[/yellow]")
        rprint("[cyan]💡 Expected to find images like: flight-*.png, image-*.png, etc.[/cyan]")
        return
        
    tasks = [(image_path, threshold, skip, take)
            for threshold in range(threshold_from, threshold_to + 1)
            for image_path in images]
    total_count = 0
    all_results = []
    all_thresholds = []

    rprint(f"[green]📁 Found {len(images)} images to process with thresholds {threshold_from}-{threshold_to}[/green]")

    process_wrapper_with_flag = partial(process_wrapper, refresh_cache=refresh_cache)
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for task in tasks:
            image_path, threshold, _, _ = task
            futures[executor.submit(process_wrapper_with_flag, task)] = task
            
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            image_path, threshold, _, _ = futures[future]
            count, df, _ = future.result()  # used_cache not needed

            now = datetime.now().strftime('%H:%M:%S')
            total_count += count
            rprint(f"[bold blue][{now}] Processed [bold][magenta]{image_path.name}[/magenta][/bold] "
                  f"(threshold=[yellow]{threshold}[/yellow]) [[green]{i}[/green]/[blue]{len(tasks)}[/blue]]: "
                  f"[cyan]{count}[/cyan] lines found[/bold blue]")
            if df is not None and not df.empty:
                all_results.append(df)
                all_thresholds.append((threshold, count))
        
    # Create a pivot table: count of lines per image and threshold
    if all_results:
        if pd is None:
            print("pandas not available - cannot create pivot tables")
            return
            
        print(f"\n[bold green]Total lines printed (threshold={threshold_from}-{threshold_to}, "
              f"skip={skip}, take={take}): {total_count}[/bold green]")
        if total_count == 0:
            rprint("[bold yellow]No lines printed.[/bold yellow]")
            return
        
        results_df = pd.concat(all_results, ignore_index=True)

        print("Results DataFrame:")
        print(results_df)

        # Create a new DataFrame for the thresholds
        thresholds_df = pd.DataFrame(all_thresholds, columns=['threshold', 'count'])
        # Sort by threshold
        thresholds_df = thresholds_df.sort_values(by='threshold')
        print("Thresholds DataFrame:")
        print(thresholds_df)

        pivot = results_df.pivot_table(
            index='image',
            columns='threshold',
            values='line',
            aggfunc='count',
            fill_value=0,
            margins=True,
            margins_name='Total'
        )
        rprint("\nPivot table (count of lines per image/threshold, with totals):")
        
        _display_pivot_table(pivot)
            
        # Create a pivot table: count of lines per threshold (totals only)
        pivot2 = results_df.pivot_table(
            index='threshold',
            values='line',
            aggfunc='count',
            fill_value=0,
            margins=True,
            margins_name='Total'
        )
        rprint("\nPivot table (count of lines per threshold, with totals):")
        _display_threshold_table(pivot2)
        
        # Sort the last pivot table (pivot2) by count ascending
        pivot2_sorted = pivot2.sort_values(by='line', ascending=True)
        rprint("\nPivot table (sorted by count ascending):")
        _display_threshold_table(pivot2_sorted)
        
        # Find the minimum count (excluding 'Total') in the sorted pivot table
        min_count = pivot2_sorted.loc[pivot2_sorted.index != 'Total', 'line'].min()
        # Get all thresholds with this minimum count
        lowest_thresholds = pivot2_sorted.loc[(pivot2_sorted['line'] == min_count) & 
                                             (pivot2_sorted.index != 'Total')].index.tolist()
        rprint(f"\n[bold green]Threshold(s) with the lowest count ({min_count}): {lowest_thresholds}[/bold green]")

        # Print the lines for those thresholds
        _display_lines_for_thresholds(lowest_thresholds, all_results)
        
    # Display summary with safe task access
    if tasks:
        threshold_range = f"threshold={tasks[0][1]}-{tasks[-1][1]}"
    else:
        threshold_range = f"threshold={threshold_from}-{threshold_to}"
    rprint(f"\nTotal lines printed ({threshold_range}, skip={skip}, take={take}): {total_count}")
    
    if 'pivot2' in locals():
        _display_chart(pivot2)


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
        print(f"Error displaying table: {e}")
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
        print(f"Error displaying threshold table: {e}")
        rprint(pivot2)


def _display_lines_for_thresholds(lowest_thresholds, all_results):
    """Display lines for the lowest thresholds."""
    for threshold in lowest_thresholds:
        rprint(f"\n[bold magenta]Lines for threshold {threshold}:[/bold magenta]")
        for df in all_results:
            lines = df[df['threshold'] == threshold]['line'].tolist()
            if lines:
                rprint(f"[bold cyan]{df['image'].iloc[0]}[/bold cyan]")
                for line in lines:
                    line_number = df[df['line'] == line]['line_number'].iloc[0]
                    rprint(f"[bold yellow]{line_number}:[/bold yellow] {line}")


def _display_chart(pivot2):
    """Display bar chart if matplotlib is available."""
    if plt is None:
        print("matplotlib not available - cannot display chart")
        return
        
    try:
        _, ax = plt.subplots(figsize=(8, 4))
        pivot2_no_total = pivot2.drop('Total', errors='ignore')
        pivot2_no_total['line'].plot(kind='bar', ax=ax, color='skyblue')
        ax.set_title('Count of Lines per Threshold')
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Count')
        plt.tight_layout()
        plt.show()
    except (ImportError, RuntimeError) as e:
        print(f"Error displaying chart: {e}")


if __name__ == "__main__":
    main_parser = argparse.ArgumentParser()
    main_parser.add_argument('--no-refresh-cache', action='store_false', dest='refresh_cache', 
                            help='Use cache if available (default: recompute and overwrite)')
    main_parser.add_argument('--max-workers', type=int, default=4, 
                            help='Maximum number of worker processes (default: 4)')
    main_parser.set_defaults(refresh_cache=True)
    main_parser.set_defaults(max_workers=4)
    main_args = main_parser.parse_args()
    batch_process(refresh_cache=main_args.refresh_cache, max_workers=main_args.max_workers)


class ThresholdOptimizer:
    """
    Wrapper class for threshold optimization functionality.
    
    This class provides a clean interface to the threshold optimization
    functions for use in other parts of the application.
    """
    
    @staticmethod
    def optimize_thresholds(refresh_cache=True, max_workers=4):
        """
        Run threshold optimization analysis.
        
        Args:
            refresh_cache: Whether to refresh the cache or use existing results
            max_workers: Maximum number of worker processes for parallel processing
        """
        return batch_process(refresh_cache=refresh_cache, max_workers=max_workers)
    
    @staticmethod
    def process_single_image(threshold=None, skip=None, take=None):
        """
        Process a single image with specified parameters.
        
        Args:
            threshold: OCR threshold value
            skip: Number of images to skip
            take: Number of images to process
        """
        return process_image(threshold=threshold, skip=skip, take=take)