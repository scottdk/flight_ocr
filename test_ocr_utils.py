"""
test_ocr_utils.py

Script to test OCR preprocessing and extraction with different Tesseract configurations.
"""

from pathlib import Path
from ocr_utils import preprocess_image, run_ocr

def process_image(threshold=None, skip=None, take=None):
    import argparse
    parser = argparse.ArgumentParser(description="Test OCR preprocessing and extraction.")
    parser.add_argument('image', nargs='?', default='images/Screenshot from 2025-08-23 10-24-54.png',
                        help='Path to the image file to test (default: images/Screenshot from 2025-08-23 10-24-12.png)')
    parser.add_argument('--tess-config', type=str, default="-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–— --psm 6 --oem 3", help='Tesseract config string')
    parser.add_argument('--threshold', type=int, default=170, help='Threshold for binarization (default: 170)')
    parser.add_argument('--skip', type=int, default=0, help='number of rows to skip (default: 0)')
    parser.add_argument('--take', type=int, default=0, help='number of rows to take (default: 0)')

    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    import re
    threshold_val = threshold if threshold is not None else args.threshold
    image_path = Path(args.image)
    img_bin = preprocess_image(image_path, debug=args.debug, threshold=threshold_val)
    # Save preprocessed image with _ prefix
    processed_dir = image_path.parent / "processed"
    processed_dir.mkdir(exist_ok=True)
    preprocessed_path = processed_dir / (image_path.stem + f"_{threshold_val}" + image_path.suffix)
    img_bin.save(preprocessed_path)
    ocr_text = run_ocr(img_bin, debug=args.debug, tess_config=args.tess_config)
    lines = ocr_text.replace('\n\n', '\n').splitlines()
    numbered_lines = list(enumerate(lines, start=1))
    skip_val = skip if skip is not None else args.skip
    take_val = take if take is not None else args.take
    price_pattern = re.compile(r'^A\$\d{1,3}(,\d{3})*$')
    if skip_val == 0:
        lines_to_check = numbered_lines
    else:
        lines_to_check = numbered_lines[skip_val:skip_val+take_val]
    filtered = [(num, line) for num, line in lines_to_check if not price_pattern.match(line.strip())]
    import pandas as pd
    if all(line[1].strip()[:3].isalpha() for line in filtered):
        count = 0
        df = pd.DataFrame()
    else:
        # count = sum(1 for _, line in filtered if not line.strip()[:3].isalpha())
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
def process_wrapper(args, refresh_cache=False):
    import sys
    import os
    import pickle
    image_path, threshold, skip, take = args
    cache_dir = os.path.join(os.path.dirname(str(image_path)), '.cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(
        cache_dir,
        f"{os.path.basename(str(image_path))}_thr{threshold}_skip{skip}_take{take}.pkl"
    )
    used_cache = False
    from datetime import datetime
    try:
        from rich import print as rprint
    except ImportError:
        rprint = print
    now = datetime.now().strftime('%H:%M:%S')
    # rprint(f"[bold blue][{now}][Worker {os.getpid()}][/bold blue] refresh_cache=[cyan]{refresh_cache}[/cyan] cache_file=[magenta]{cache_file}[/magenta] exists=[yellow]{os.path.exists(cache_file)}[/yellow]")
    if not refresh_cache and os.path.exists(cache_file):
        rprint(f"[bold green][{now}][Worker {os.getpid()}] loading from cache: [magenta]{cache_file}[/magenta][/bold green]")
        with open(cache_file, 'rb') as f:
            count, df = pickle.load(f)
        used_cache = True
        return count, df, used_cache
    else:
        rprint(f"[bold yellow][{now}][Worker {os.getpid()}] recomputing and writing to cache: [magenta]{cache_file}[/magenta][/bold yellow]")
    sys.argv = [sys.argv[0], str(image_path), '--threshold', str(threshold), '--skip', str(skip), '--take', str(take)]
    from test_ocr_utils import process_image
    count, df = process_image(threshold=threshold, skip=skip, take=take)
    with open(cache_file, 'wb') as f:
        pickle.dump((count, df), f)
    return count, df, used_cache

def batch_process(refresh_cache=False, max_workers=2):
    from pathlib import Path
    from datetime import datetime
    try:
        from rich import print as rprint
    except ImportError:
        rprint = print
    import concurrent.futures
    import os
    # print(f"[Parent] {os.getpid()} refresh_cache={refresh_cache}", flush=True)
    now = datetime.now().strftime('%H:%M:%S')
    rprint(f"[bold magenta][{now}][Parent {os.getpid()}] refresh_cache={refresh_cache} max_workers={max_workers}[/bold magenta]")
    images_dir = Path("images")
    images = sorted([f for f in images_dir.glob("*.png") if not f.name.startswith("_")])[:2]
    threshold_from = 170
    threshold_to = 171
    skip = 0
    take = 9
    tasks = [(image_path, threshold, skip, take)
             for threshold in range(threshold_from, threshold_to + 1)
             for image_path in images]
    total_count = 0
    all_results = []

    from functools import partial
    process_wrapper_with_flag = partial(process_wrapper, refresh_cache=refresh_cache)
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for idx, task in enumerate(tasks, 1):
            image_path, threshold, _, _ = task
            now = datetime.now().strftime('%H:%M:%S')
            rprint(f"[bold cyan][{now}] Submitting [bold][magenta]{image_path.name}[/magenta][/bold] (threshold=[yellow]{threshold}[/yellow]) [[green]{idx}[/green]/[blue]{len(tasks)}[/blue]][/bold cyan]")
            futures[executor.submit(process_wrapper_with_flag, task)] = task
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            image_path, threshold, _, _ = futures[future]
            try:
                count, df, used_cache = future.result()
                now = datetime.now().strftime('%H:%M:%S')
                if used_cache:
                    rprint(f"[bold green][{now}] Used cache [bold][magenta]{image_path.name}[/magenta][/bold] (threshold=[yellow]{threshold}[/yellow]) [[green]{i}[/green]/[blue]{len(tasks)}[/blue]][/bold green]")
                else:
                    rprint(f"[bold yellow][{now}] Processed [bold][magenta]{image_path.name}[/magenta][/bold] (threshold=[yellow]{threshold}[/yellow]) [[green]{i}[/green]/[blue]{len(tasks)}[/blue]][/bold yellow]")
                total_count += count
                if df is not None and not df.empty:
                    all_results.append(df)
            except Exception as e:
                rprint(f"\nError processing [bold red]{image_path}[/bold red] (threshold={threshold}): {e}")

    # Print DataFrame and summary after all processing
    import pandas as pd
    if all_results:
        results_df = pd.concat(all_results, ignore_index=True)
        results_df.index = results_df.index + 1
        rprint(results_df)
    # Create a pivot table: count of lines per image and threshold
    if all_results:
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
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("image", style="bold")
            col_colors = ["cyan", "green", "magenta", "blue", "red", "bright_cyan", "bright_green", "bright_magenta", "bright_blue", "bright_red"]
            col_styles = []
            for i, col in enumerate(pivot.columns):
                style = col_colors[i % len(col_colors)]
                col_styles.append(style)
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
        except ImportError:
            rprint(pivot)
            
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
        except ImportError:
            rprint(pivot2)

        import matplotlib.pyplot as plt

        # # Plot bar chart for the last pivot table (pivot2)
        # fig, ax = plt.subplots(figsize=(8, 4))
        # pivot2_no_total = pivot2.drop('Total', errors='ignore')
        # pivot2_no_total['line'].plot(kind='bar', ax=ax, color='skyblue')
        # ax.set_title('Count of Lines per Threshold')
        # ax.set_xlabel('Threshold')
        # ax.set_ylabel('Count')
        # plt.tight_layout()
        # plt.show()
        
        
        # Sort the last pivot table (pivot2) by count ascending
        pivot2_sorted = pivot2.sort_values(by='line', ascending=True)
        rprint("\nPivot table (sorted by count ascending):")
        try:
            table2_sorted = Table(show_header=True, header_style="bold magenta")
            table2_sorted.add_column("threshold", style="bold")
            table2_sorted.add_column("count", style="cyan")
            for idx, row in pivot2_sorted.iterrows():
                if str(idx) != 'Total':
                    table2_sorted.add_row(str(idx), str(row['line']))
            if 'Total' in pivot2_sorted.index:
                total_row = pivot2_sorted.loc['Total']
                table2_sorted.add_row(
                    '[b yellow]Total[/b yellow]',
                    f'[b yellow]{total_row["line"]}[/b yellow]',
                    end_section=True
                )
            console.print(table2_sorted)
        except ImportError:
            rprint(pivot2_sorted)
        
        # Plot bar chart for the last pivot table (pivot2)
        fig, ax = plt.subplots(figsize=(8, 4))
        pivot2_no_total = pivot2_sorted.drop('Total', errors='ignore')
        pivot2_no_total['line'].plot(kind='bar', ax=ax, color='skyblue')
        ax.set_title('Count of Lines per Threshold')
        ax.set_xlabel('Threshold')
        ax.set_ylabel('Count')
    plt.tight_layout()
    plt.show(block=True)
    import time
    time.sleep(1)  # Give the plot window time to appear before script exits
            
        
    rprint(f"\nTotal lines printed (threshold={tasks[0][1]}-{tasks[-1][1]}, skip={skip}, take={take}): {total_count}")


if __name__ == "__main__":
    import argparse
    from rich.console import Console
    from rich.table import Table
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-refresh-cache', action='store_false', dest='refresh_cache', help='Use cache if available (default: recompute and overwrite)')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum number of worker processes (default: 2)')
    parser.set_defaults(refresh_cache=False)
    parser.set_defaults(max_workers=2)
    args = parser.parse_args()
    batch_process(refresh_cache=args.refresh_cache, max_workers=args.max_workers)