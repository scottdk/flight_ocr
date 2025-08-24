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
import sys
from datetime import datetime
from functools import partial
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
from flight_ocr.core.image_processor import process_image_for_ocr

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

def process_image(threshold=None, skip=None, take=None, no_cache=False):
    """
    Process a single image with OCR preprocessing and extraction.
    
    Args:
        threshold: Binarization threshold (default from args)
        skip: Number of rows to skip (default from args) 
        take: Number of rows to take (default from args)
        no_cache: Skip cache, perform OCR, and update cache with new results
        
    Returns:
        tuple: (count, DataFrame) containing count of filtered lines and DataFrame with results
    """
    parser = argparse.ArgumentParser(description="Test OCR preprocessing and extraction.")
    parser.add_argument('image', nargs='?', default='data/input/raw/flight-2025-08-23 10-24-54.png',
                        help='Path to the image file to test (default: data/input/raw/flight-2025-08-23 10-24-12.png)')
    parser.add_argument('--tess-config', type=str, 
                        default="-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–— --psm 6 --oem 3", 
                        help='OCR engine configuration string')
    parser.add_argument('--threshold', type=int, default=170, help='Threshold for binarization (default: 170)')
    parser.add_argument('--skip', type=int, default=0, help='number of rows to skip (default: 0)')
    parser.add_argument('--take', type=int, default=0, help='number of rows to take (default: 0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    parsed_args = parser.parse_args()

    threshold_val = threshold if threshold is not None else parsed_args.threshold
    image_path = Path(parsed_args.image)

    # Use the single point of access for OCR processing
    try:
        rprint(f"[cyan]🔄 Processing image:[/cyan] [bold magenta]{image_path}[/bold magenta] [yellow](threshold={threshold_val})[/yellow]")
        ocr_text = process_image_for_ocr(
            image_path=image_path,
            threshold=threshold_val,
            no_cache=no_cache,
            debug=parsed_args.debug,
            tess_config=parsed_args.tess_config
        )
    except Exception as e:
        # Log OCR error with context
        rprint(f"[orange3]⚠️  OCR error processing {image_path}: {str(e)}[/orange3]")
        # Handle OCR errors generically - the threshold optimizer shouldn't know about specific OCR backends
        rprint(f"[red]❌ OCR Error: {str(e)}[/red]")
        raise
    
    # Process the OCR text (threshold optimizer's responsibility)
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
def process_wrapper(task_args, no_cache=False):
    """
    Wrapper function for multiprocessing to handle image processing tasks.
    
    This function is now cache-agnostic - all caching is handled by image_processor.
    
    Args:
        task_args: Tuple of (image_path, threshold, skip, take)
        no_cache: Whether to skip caching (passed to image_processor)
        
    Returns:
        tuple: (count, DataFrame)
    """
    image_path, threshold, skip, take = task_args
    now = datetime.now().strftime('%H:%M:%S')
    
    # Process the image using the image processor (which handles all caching)
    try:
        rprint(f"[bold yellow][{now}][Worker {os.getpid()}] processing: [magenta]{image_path.name}[/magenta] (threshold={threshold})[/bold yellow]")
        sys.argv = [sys.argv[0], str(image_path), '--threshold', str(threshold), '--skip', str(skip), '--take', str(take)]
        count, df = process_image(threshold=threshold, skip=skip, take=take, no_cache=no_cache)
        return count, df
    except (ImportError, FileNotFoundError, ValueError) as exc:
        rprint(f"[red]❌ Error processing {image_path}: {exc}[/red]")
        return 0, None
    except Exception as exc:
        # Handle OCR errors generically
        rprint(f"[orange3]⚠️  OCR error processing {image_path}: {exc}[/orange3]")
        return 0, None

def batch_process(no_cache=False, max_workers=2, thresholds="171-173", 
                 skip=0, take=9, image_file=None, image_dir=None):
    """
    Process multiple images in batch using multiprocessing.
    
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
        
    tasks = [(image_path, threshold, skip, take)
            for threshold in threshold_values
            for image_path in images]
    total_count = 0
    all_results = []
    all_thresholds = []

    # Display threshold info
    if len(threshold_values) == 1:
        threshold_display = str(threshold_values[0])
    elif len(threshold_values) <= 5:
        threshold_display = ",".join(map(str, threshold_values))
    else:
        threshold_display = f"{threshold_from}-{threshold_to} ({len(threshold_values)} values)"
    
    rprint(f"[green]📁 Found {len(images)} images to process with thresholds: {threshold_display}[/green]")

    process_wrapper_with_flag = partial(process_wrapper, no_cache=no_cache)
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for task in tasks:
            image_path, threshold, _, _ = task
            futures[executor.submit(process_wrapper_with_flag, task)] = task
            
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            image_path, threshold, _, _ = futures[future]
            try:
                count, df = future.result()  # Simplified return - no used_cache flag
            except concurrent.futures.process.BrokenProcessPool as e:
                rprint(f"[red]❌ Process pool error for {image_path.name} (threshold={threshold}): {e}[/red]")
                rprint("[yellow]💡 This often indicates an OCR backend issue.[/yellow]")
                continue
            except Exception as e:
                rprint(f"[red]❌ Error processing {image_path.name} (threshold={threshold}): {e}[/red]")
                continue

            now = datetime.now().strftime('%H:%M:%S')
            total_count += count
            rprint(f"[bold blue][{now}] Processed [bold][magenta]{image_path.name}[/magenta][/bold] "
                  f"(threshold=[yellow]{threshold}[/yellow]) [[green]{i}[/green]/[blue]{len(tasks)}[/blue]]: "
                  f"[cyan]{count}[/cyan] issues found[/bold blue]")
            if df is not None and not df.empty:
                all_results.append(df)
                all_thresholds.append((threshold, count))
        
    # Create a pivot table: count of issues per image and threshold
    if all_results:
        if pd is None:
            rprint("[yellow]⚠️  pandas not available - cannot create pivot tables[/yellow]")
            return
            
        rprint(f"\n[bold green]📊 Total issues found (thresholds: {threshold_display}, "
              f"skip={skip}, take={take}): {total_count}[/bold green]")
        if total_count == 0:
            rprint("[bold yellow]✨ No issues found.[/bold yellow]")
            return
        
        results_df = pd.concat(all_results, ignore_index=True)

        rprint("[blue]📋 Results DataFrame:[/blue]")
        print(results_df)

        # Create a new DataFrame for the thresholds
        thresholds_df = pd.DataFrame(all_thresholds, columns=['threshold', 'count'])
        # Sort by threshold
        thresholds_df = thresholds_df.sort_values(by='threshold')
        rprint("[blue]🎯 Thresholds DataFrame:[/blue]")
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
        rprint("\n[bold cyan]📊 Pivot table (count of issues per image/threshold, with totals):[/bold cyan]")
        
        _display_pivot_table(pivot)
            
        # Create a pivot table: count of issues per threshold (totals only)
        pivot2 = results_df.pivot_table(
            index='threshold',
            values='line',
            aggfunc='count',
            fill_value=0,
            margins=True,
            margins_name='Total'
        )
        rprint("\n[bold magenta]📈 Pivot table (count of issues per threshold, with totals):[/bold magenta]")
        _display_threshold_table(pivot2)
        
        # Sort the last pivot table (pivot2) by count ascending
        pivot2_sorted = pivot2.sort_values(by='line', ascending=True)
        rprint("\n[bold yellow]🏆 Pivot table (sorted by count ascending):[/bold yellow]")
        _display_threshold_table(pivot2_sorted)
        
        # Find the minimum count (excluding 'Total') in the sorted pivot table
        min_count = pivot2_sorted.loc[pivot2_sorted.index != 'Total', 'line'].min()
        # Get all thresholds with this minimum count
        lowest_thresholds = pivot2_sorted.loc[(pivot2_sorted['line'] == min_count) & 
                                             (pivot2_sorted.index != 'Total')].index.tolist()
        rprint(f"\n[bold green]🎯 Threshold(s) with the lowest count ({min_count}): {lowest_thresholds}[/bold green]")

        # Print the issues for those thresholds
        _display_issues_for_thresholds(lowest_thresholds, all_results)
        
    # Display summary with safe task access
    if tasks:
        threshold_range = f"thresholds: {threshold_display}"
    else:
        threshold_range = f"thresholds: {threshold_display}"
    rprint(f"\n[bold cyan]📋 Total issues printed ({threshold_range}, skip={skip}, take={take}): {total_count}[/bold cyan]")
    
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
            issues = df[df['threshold'] == threshold]['issue'].tolist()
            if issues:
                rprint(f"[bold cyan]{df['image'].iloc[0]}[/bold cyan]")
                for issue in issues:
                    issue_number = df[df['issue'] == issue]['issue_number'].iloc[0]
                    rprint(f"[bold yellow]{issue_number}:[/bold yellow] {issue}")


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
    main_parser = argparse.ArgumentParser(description="Optimize OCR thresholds for flight image processing")
    main_parser.add_argument('--no-cache', action='store_true', dest='no_cache',
                            help='Skip cache, perform OCR, and update cache with new results (default: use cache if available)')
    main_parser.add_argument('--max-workers', type=int, default=4, 
                            help='Maximum number of worker processes (default: 4)')
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
    main_parser.set_defaults(max_workers=4)
    main_args = main_parser.parse_args()
    
    # Handle --check-ocr option
    if main_args.check_ocr:
        rprint("[bold cyan]🔍 OCR Backend Installation Check[/bold cyan]")
        rprint("[yellow]⚠️  OCR backend checks have been moved to the processing layer.[/yellow]")
        rprint("[cyan]💡 The threshold optimizer is now backend-agnostic and doesn't directly check OCR engines.[/cyan]")
        rprint("[green]✅ Try processing an image to see if OCR is working properly.[/green]")
        exit(0)
    
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