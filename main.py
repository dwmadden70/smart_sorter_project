"""
main.py
10th-Grade Computer Science Interactive Demo & Visual Timing Comparison
Run from the project root:
    python main.py
    python main.py --file path/to/your_data.json
    python main.py --file path/to/your_data.json --custom-algo bubble
    python main.py --runalltests
"""

import argparse
from contextlib import redirect_stdout
import csv
from datetime import datetime
import inspect
import io
import json
from pathlib import Path
import random
import re
import sys
import time
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "tests" / "data"
REPORTS_DIR = PROJECT_ROOT / "tests" / "results"
TESTS_DIR = PROJECT_ROOT / "tests"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from smart_sorter import _SORT_METHOD_DECISION_MATRIX, smart_sort


class _TeeStream:
    """Writes output simultaneously to sys.stdout and an in-memory StringIO buffer."""

    def __init__(self, terminal_stream, capture_buffer):
        self.terminal_stream = terminal_stream
        self.capture_buffer = capture_buffer

    def write(self, text):
        self.terminal_stream.write(text)
        self.capture_buffer.write(text)
        return len(text)

    def flush(self):
        self.terminal_stream.flush()
        self.capture_buffer.flush()


def _format_markdown_report(raw_console_output, dataset_file, command_used):
    """Converts captured console diagnostics into a clean, structured Markdown report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = raw_console_output.splitlines()

    md_lines = [
        f"# Tests for {dataset_file}",
        "",
        f"- **Generated:** {timestamp}",
        f"- **Command:** `{command_used}`",
        "",
        "---",
        "",
    ]

    in_code_block = False

    def close_code_block():
        nonlocal in_code_block
        if in_code_block:
            md_lines.append("```")
            md_lines.append("")
            in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped and set(stripped) <= {"=", "-"} and len(stripped) >= 20:
            continue

        if stripped.startswith("[Error]"):
            close_code_block()
            err_msg = stripped[len("[Error]"):].strip()
            md_lines.append(f"> **Error:** {err_msg}")
            md_lines.append("")
            continue

        if line.startswith("  SMART SORTER:") or line.startswith("  VISUAL TIMING COMPARISON:"):
            close_code_block()
            md_lines.append(f"## {stripped}")
            md_lines.append("")
            continue

        if stripped.startswith("[Lesson ") or stripped.startswith("--- Benchmark "):
            close_code_block()
            heading = stripped.strip("- ").strip()
            md_lines.append(f"### {heading}")
            md_lines.append("")
            continue

        if stripped == "[smart_sort Classroom Report]":
            close_code_block()
            md_lines.append("#### Classroom Diagnostic Report")
            md_lines.append("")
            continue

        if stripped.startswith("* "):
            close_code_block()
            bullet_body = stripped[2:]
            if bullet_body.startswith("type ="):
                label, val = bullet_body.split("=", 1)
                md_lines.append(f"- **{label.strip()}:** {val.strip()}")
            elif ":" in bullet_body:
                label, val = bullet_body.split(":", 1)
                md_lines.append(f"- **{label.strip()}:** {val.strip()}")
            elif "=" in bullet_body:
                label, val = bullet_body.split("=", 1)
                md_lines.append(f"- **{label.strip()}:** {val.strip()}")
            else:
                md_lines.append(f"- {bullet_body}")
            continue

        if stripped.startswith("[Visual Speed Comparison]"):
            close_code_block()
            md_lines.append("#### Visual Speed Comparison")
            md_lines.append("")
            md_lines.append("```text")
            in_code_block = True
            continue

        if in_code_block:
            if stripped.startswith("Result:"):
                close_code_block()
                md_lines.append(f"> **{stripped}**")
                md_lines.append("")
            elif stripped:
                md_lines.append(line.rstrip())
            continue

        if stripped.startswith("[Preview:"):
            close_code_block()
            md_lines.append(f"#### {stripped.strip('[]')}")
            md_lines.append("")
            md_lines.append("```text")
            in_code_block = True
            continue

        if stripped.startswith("-> "):
            close_code_block()
            md_lines.append(f"- **Takeaway:** {stripped[3:]}")
            md_lines.append("")
            continue

        if stripped:
            md_lines.append(stripped)

    close_code_block()
    return "\n".join(md_lines).strip() + "\n"


def save_markdown_report(raw_console_output, report_path, title, command_used):
    """Writes the formatted Markdown report into the project's tests/results/ directory."""
    target = Path(report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    markdown_text = _format_markdown_report(raw_console_output, title, command_used)
    target.write_text(markdown_text, encoding="utf-8")
    return target


def _to_camel_case(raw_text):
    """Removes underscores and non-alphanumeric separators and converts text to CamelCase."""
    tokens = re.split(r"[^A-Za-z0-9]+", raw_text)
    return "".join(tok[:1].upper() + tok[1:] for tok in tokens if tok)


def _walk_test_suite(suite):
    """Recursively yields individual unittest.TestCase instances from a TestSuite."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _walk_test_suite(item)
        else:
            yield item


def _extract_data_dir_filename(test_case):
    """Returns the filename inside tests/data/ referenced by a direct dataset unit test, or None."""
    if test_case._testMethodName.startswith("test_cli_"):
        return None
    method = getattr(test_case, test_case._testMethodName, None)
    if method is None:
        return None
    try:
        src = inspect.getsource(method)
    except (OSError, TypeError):
        return None
    match = re.search(r'DATA_DIR\s*/\s*["\']([^"\']+)["\']', src)
    return match.group(1) if match else None


def _get_sort_source_info(chosen_sort):
    """Looks up source_url and install_cmd in _SORT_METHOD_DECISION_MATRIX if non-built-in."""
    if chosen_sort.startswith("Custom Algorithm"):
        entry = _SORT_METHOD_DECISION_MATRIX.get("Custom Algorithm", {})
    else:
        entry = _SORT_METHOD_DECISION_MATRIX.get(chosen_sort, {})
    return entry.get("source_url"), entry.get("install_cmd")


def run_all_tests_with_reports(output_dir=None, extra_unittest_args=None):
    """
    Discovers and runs dataset unit tests in tests/, writing ONE concise Markdown report
    per file in tests/data/ into tests/results/ named <DatasetName>.md in CamelCase.
    """
    target_dir = Path(output_dir) if output_dir else REPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    for old_md in target_dir.glob("*.md"):
        old_md.unlink()

    loader = unittest.defaultTestLoader
    patterns = [arg for arg in (extra_unittest_args or []) if not arg.startswith("-")]
    if patterns:
        suite = unittest.TestSuite()
        for pat in patterns:
            if Path(pat).is_file():
                suite.addTests(loader.discover(str(Path(pat).parent), pattern=Path(pat).name))
            else:
                suite.addTests(loader.loadTestsFromName(pat))
    else:
        suite = loader.discover(str(TESTS_DIR))

    all_cases = list(_walk_test_suite(suite))
    if patterns:
        test_cases = all_cases
    else:
        test_cases = [tc for tc in all_cases if _extract_data_dir_filename(tc) is not None]

    print("=" * 72)
    print(f"  SMART SORTER: RUNNING {len(test_cases)} DATASET TESTS WITH MARKDOWN REPORTS")
    print("=" * 72)

    passed = 0
    failed = 0
    skipped = 0
    written_datasets = set()

    for test_case in test_cases:
        test_name = test_case._testMethodName
        buf = io.StringIO()
        result = unittest.TestResult()
        with redirect_stdout(buf):
            test_case.run(result)

        captured = buf.getvalue()
        dataset_match = re.search(r"Dataset File\s*:\s*([^\n]+)", captured)
        dataset_file = dataset_match.group(1).strip() if dataset_match else _extract_data_dir_filename(test_case)

        algo_match = re.search(r"Chosen sort method should be:\s*([^\n]+)", captured)
        raw_algo = algo_match.group(1).strip() if algo_match else "Unknown"
        clean_algo = re.sub(r"\s*\(see readme\.md\)\s*$", "", raw_algo).strip()

        why_match = re.search(r"Why this won:\s*([^\n]+)", captured)
        why_text = why_match.group(1).strip() if why_match else "No diagnostic explanation recorded."

        if result.skipped:
            skipped += 1
            print(f"  [SKIPPED] {test_name} ({result.skipped[0][1]})")
            continue

        if not result.wasSuccessful():
            failed += 1
            err_tuple = (result.failures + result.errors)[0]
            print(f"  [FAIL   ] {test_name}")
            print(err_tuple[1])
            continue

        passed += 1

        if not dataset_file:
            print(f"  [PASS   ] {test_name} (no dataset report emitted)")
            continue

        if dataset_file in written_datasets:
            print(f"  [PASS   ] {test_name} (already reported)")
            continue

        written_datasets.add(dataset_file)

        dataset_stem = Path(dataset_file).stem
        dataset_camel = _to_camel_case(dataset_stem) or "Dataset"
        report_filename = f"{dataset_camel}.md"
        report_path = target_dir / report_filename

        source_url, install_cmd = _get_sort_source_info(clean_algo)

        md_lines = [
            f"# Tests for {dataset_file}",
            "",
            f"- **Best Sort Chosen:** {clean_algo}",
            f"- **Why:** {why_text}",
        ]
        if source_url is not None:
            md_lines.append(f"- **Source URL:** {source_url}")
            if install_cmd:
                md_lines.append(f"- **Install:** `{install_cmd}`")

        report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        print(f"  [PASS   ] {test_name}")

    print("-" * 72)
    print(
        f"  Summary: {passed} passed, {failed} failed, {skipped} skipped"
    )
    print(
        f"           {len(written_datasets)} dataset reports saved to: tests\\results"
    )
    if failed > 0:
        sys.exit(1)


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(filepath):
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_lines(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_custom_file(filepath):
    """Loads a student-supplied .json, .csv, or .txt dataset from any path."""
    path = Path(filepath).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Could not find file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        data = load_json(path)
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, list):
                    return val
            raise ValueError(
                "JSON root is an object with no list of records. "
                "Provide a JSON array (e.g., [{...}, {...}]) or an object containing a list."
            )
        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of items to sort.")
        return data

    if suffix == ".csv":
        return load_csv(path)

    if suffix in (".txt", ".log"):
        return load_lines(path)

    raise ValueError(
        f"Unsupported file extension '{suffix}'. Please provide a .json, .csv, or .txt file."
    )


def bubble_sort_paired(paired_items, reverse=False):
    """Sample O(n^2) Bubble Sort over (key, original_item) pairs for classroom demos."""
    arr = list(paired_items)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            should_swap = arr[j][0] < arr[j + 1][0] if reverse else arr[j][0] > arr[j + 1][0]
            if should_swap:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return [orig for _, orig in arr]


def selection_sort_paired(paired_items, reverse=False):
    """Sample O(n^2) Selection Sort over (key, original_item) pairs for classroom demos."""
    arr = list(paired_items)
    n = len(arr)
    for i in range(n):
        best_idx = i
        for j in range(i + 1, n):
            is_better = arr[j][0] > arr[best_idx][0] if reverse else arr[j][0] < arr[best_idx][0]
            if is_better:
                best_idx = j
        arr[i], arr[best_idx] = arr[best_idx], arr[i]
    return [orig for _, orig in arr]


def insertion_sort_paired(paired_items, reverse=False):
    """Sample O(n) best / O(n^2) worst Insertion Sort over (key, original_item) pairs."""
    arr = list(paired_items)
    for i in range(1, len(arr)):
        current = arr[i]
        j = i - 1
        while j >= 0 and (arr[j][0] < current[0] if reverse else arr[j][0] > current[0]):
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = current
    return [orig for _, orig in arr]


CUSTOM_ALGORITHMS = {
    "bubble": (bubble_sort_paired, "Bubble Sort", "O(n^2)"),
    "selection": (selection_sort_paired, "Selection Sort", "O(n^2)"),
    "insertion": (insertion_sort_paired, "Insertion Sort", "O(n) best / O(n^2) worst"),
}


def render_bar_chart(label_a, sec_a, label_b, sec_b, width=36):
    """Draws an ASCII side-by-side speed comparison bar chart in seconds."""
    peak = max(sec_a, sec_b, 0.000001)
    len_a = max(1, int(round((sec_a / peak) * width)))
    len_b = max(1, int(round((sec_b / peak) * width)))

    print(f"  {label_a:<22} | {'#' * len_a:<{width}} | {sec_a:.4f} sec")
    print(f"  {label_b:<22} | {'#' * len_b:<{width}} | {sec_b:.4f} sec")


def run_benchmark_comparison(title, dataset, standard_key_fn=None):
    """Runs standard sorted() vs smart_sort() and prints a visual speedup comparison."""
    print(f"\n--- {title} ({len(dataset):_} records) ---")

    t0 = time.perf_counter()
    if standard_key_fn:
        baseline_result = sorted(dataset, key=standard_key_fn)
    else:
        baseline_result = sorted(dataset)
    baseline_sec = time.perf_counter() - t0

    t1 = time.perf_counter()
    smart_result = smart_sort(dataset, explain=True)
    smart_sec = time.perf_counter() - t1

    assert len(baseline_result) == len(smart_result)

    print("\n  [Visual Speed Comparison]")
    render_bar_chart("Standard sorted()", baseline_sec, "smart_sort()", smart_sec)

    diff = baseline_sec - smart_sec
    if diff > 0:
        speedup = baseline_sec / max(smart_sec, 0.000001)
        print(f"  Result: smart_sort() finished {diff:.4f} seconds faster ({speedup:.2f}x speedup)!")
    else:
        overhead = abs(diff)
        print(
            f"  Result: Standard sorted() was {overhead:.4f} seconds faster "
            "(Python's compiled C Timsort has lower constant-factor overhead than pure-Python buckets at this size)."
        )


def run_custom_file_demo(filepath, sort_key=None, reverse=False, preview_count=5, custom_algo=None):
    """Loads a student file, runs smart_sort with classroom diagnostics, and previews results."""
    print("=" * 72)
    print("  SMART SORTER: CUSTOM STUDENT FILE INSPECTOR")
    print("=" * 72)
    print(f"  Target File : {filepath}")
    if sort_key:
        print(f"  Sort Key    : {sort_key}")
    if custom_algo:
        print(f"  Custom Algo : {custom_algo}")
    print(f"  Order       : {'Descending (--reverse)' if reverse else 'Ascending'}")
    print("-" * 72)

    custom_fn = None
    custom_name = None
    custom_big_o = "O(n log n)"
    if custom_algo:
        custom_fn, custom_name, custom_big_o = CUSTOM_ALGORITHMS[custom_algo]

    try:
        dataset = load_custom_file(filepath)
        sorted_data = smart_sort(
            dataset,
            sort_key=sort_key,
            reverse=reverse,
            explain=True,
            custom_sort_fn=custom_fn,
            custom_sort_name=custom_name,
            custom_big_o=custom_big_o,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError, csv.Error) as exc:
        print(f"\n[Error] {exc}")
        return False

    if sorted_data:
        shown = min(preview_count, len(sorted_data))
        print(f"\n  [Preview: First {shown} of {len(sorted_data):_} Sorted Items]")
        for idx, item in enumerate(sorted_data[:shown], start=1):
            print(f"  {idx}. {item}")
    else:
        print("\n  [Preview] The file contained 0 records.")
    return True


def run_classroom_lessons():
    """Runs the built-in 7-lesson curriculum and visual Big O timing benchmarks."""
    print("=" * 72)
    print("  SMART SORTER: 10TH-GRADE BIG O & ALGORITHM SELECTION LAB")
    print("=" * 72)

    print("\n[Lesson 1] Standard E-Commerce Product JSON")
    products = load_json(DATA_DIR / "products_standard.json")
    sorted_products = smart_sort(products, explain=True)
    print(f"  -> Cheapest item: {sorted_products[0]['name']} (${sorted_products[0]['price']})")

    print("\n[Lesson 2] Schema.org JSON-LD Products (Nested String Price)")
    schema_products = load_json(DATA_DIR / "products_schema_org.json")
    sorted_schema = smart_sort(schema_products, explain=True)
    print(f"  -> Cheapest JSON-LD item: {sorted_schema[0]['name']} (${sorted_schema[0]['offers']['price']})")

    print("\n[Lesson 3] 2,500 Student Test Scores (0 to 50 Points)")
    scores = load_json(DATA_DIR / "student_scores.json")
    sorted_scores = smart_sort(scores, reverse=True, explain=True)
    print(f"  -> Top student: {sorted_scores[0]['studentId']} with {sorted_scores[0]['pointsEarned']} pts")

    print("\n[Lesson 4] Unfamiliar Weather Sensor CSV (Auto Key Discovery)")
    weather_rows = load_csv(DATA_DIR / "weather_telemetry.csv")
    sorted_weather = smart_sort(weather_rows, explain=True)
    print(f"  -> First reading sorted: {sorted_weather[0]}")

    print("\n[Lesson 5] Famous Author Quotes (Variable-Length Strings)")
    quotes = load_lines(DATA_DIR / "author_quotes.txt")
    sorted_quotes = smart_sort(quotes, explain=True)
    print(f"  -> First quote alphabetically: {sorted_quotes[0][:55]}...")

    print("\n[Lesson 6] 60,000 Uniformly Distributed Floating-Point Numbers")
    rng = random.Random(42)
    uniform_floats = [rng.uniform(0.0, 1000.0) for _ in range(60_000)]
    smart_sort(uniform_floats, explain=True)

    print("\n[Lesson 7] 120,000 Warehouse Barcode IDs")
    barcodes = [rng.randint(100_000_000, 999_999_999) for _ in range(120_000)]
    smart_sort(barcodes, explain=True)

    print("\n" + "=" * 72)
    print("  VISUAL TIMING COMPARISON: standard sorted() vs. smart_sort()")
    print("=" * 72)

    large_exam_scores = [
        {"studentId": f"STU-{i:06d}", "pointsEarned": rng.randint(0, 50)}
        for i in range(150_000)
    ]
    run_benchmark_comparison(
        "Benchmark A: 150,000 Student Exam Records (Bounded 0-50 Integers)",
        large_exam_scores,
        standard_key_fn=lambda row: row["pointsEarned"],
    )

    large_floats = [rng.uniform(0.0, 1000.0) for _ in range(100_000)]
    run_benchmark_comparison(
        "Benchmark B: 100,000 Uniformly Distributed Sensor Floats",
        large_floats,
    )

    large_barcodes = [rng.randint(100_000_000, 999_999_999) for _ in range(150_000)]
    run_benchmark_comparison(
        "Benchmark C: 150,000 Nine-Digit Warehouse Barcodes",
        large_barcodes,
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="10th-Grade Big O & Adaptive Sorting Classroom Lab"
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="Path to a custom .json, .csv, or .txt file to inspect and sort.",
    )
    parser.add_argument(
        "-k",
        "--key",
        type=str,
        default=None,
        help="Optional field name or dotted path (e.g., 'offers.price') when using --file.",
    )
    parser.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="Sort in descending order when using --file.",
    )
    parser.add_argument(
        "-p",
        "--preview",
        type=int,
        default=5,
        help="Number of sorted items to preview when using --file (default: 5).",
    )
    parser.add_argument(
        "-c",
        "--custom-algo",
        type=str,
        choices=sorted(CUSTOM_ALGORITHMS.keys()),
        default=None,
        help="Run a sample custom sorting algorithm ('bubble', 'selection', or 'insertion') on --file.",
    )
    parser.add_argument(
        "-o",
        "--report-out",
        type=str,
        default=None,
        help="Optional custom output path or directory for generated Markdown reports (defaults to tests/results/).",
    )
    parser.add_argument(
        "--runalltests",
        action="store_true",
        help="Run dataset unit tests in tests/ and output one CamelCase Markdown report per tests/data file into tests/results/.",
    )
    return parser.parse_known_args(argv)


def main():
    args, unknown_args = parse_args()

    if args.runalltests:
        run_all_tests_with_reports(output_dir=args.report_out, extra_unittest_args=unknown_args)
        return

    if unknown_args:
        parse_args(sys.argv[1:])

    capture_buffer = io.StringIO()
    tee = _TeeStream(sys.stdout, capture_buffer)
    command_used = "python " + " ".join(sys.argv)

    if args.file:
        stem = Path(args.file).stem
        default_report = REPORTS_DIR / f"custom_inspection_{stem}.md"
        report_title = f"Smart Sorter Inspection Report: {Path(args.file).name}"
    else:
        default_report = REPORTS_DIR / "smart_sorter_classroom_report.md"
        report_title = "Smart Sorter Classroom Lab & Benchmark Report"

    report_target = Path(args.report_out) if args.report_out else default_report
    succeeded = True

    with redirect_stdout(tee):
        if args.file:
            succeeded = run_custom_file_demo(
                filepath=args.file,
                sort_key=args.key,
                reverse=args.reverse,
                preview_count=max(0, args.preview),
                custom_algo=args.custom_algo,
            )
        else:
            run_classroom_lessons()

    saved_path = save_markdown_report(
        raw_console_output=capture_buffer.getvalue(),
        report_path=report_target,
        title=report_title,
        command_used=command_used,
    )
    try:
        rel_path = saved_path.relative_to(PROJECT_ROOT)
    except ValueError:
        rel_path = saved_path
    print(f"\n[Report Saved] Formatted Markdown report written to: {rel_path}")
    if not succeeded:
        sys.exit(1)


if __name__ == "__main__":
    main()
