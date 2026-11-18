# Smart Sorter Project (10th-Grade Computer Science Edition)

An adaptive Python sorting helper (`src/smart_sorter.py`) that automatically inspects unknown input data at runtime, detects data types and JSON/CSV schemas, selects the best Big O sorting algorithm, prints student-friendly explanations with wall-clock timing in seconds, and saves formatted Markdown reports to `tests/results/`.

## Project Structure

```text
smart_sorter_project/
├── README.md
├── pyproject.toml
├── main.py                          # Interactive lessons, CLI file inspector, & timing benchmarks
├── lessons/                         # Self-paced 10th-grade student labs and coding starters
│   ├── 01_big_o_scavenger_hunt.md
│   ├── 02_custom_sort_starter.py
│   ├── 03_breaking_the_profiler.md
│   └── 04_schema_discovery_lab.md
├── src/
│   └── smart_sorter.py              # Standalone adaptive sort helper module
└── tests/
    ├── __init__.py
    ├── test_smart_sorter.py         # Unit tests covering all algorithms, decision matrix, & datasets
    ├── results/                     # Auto-generated Markdown reports from CLI and test runs
    └── data/
        ├── products_standard.json
        ├── products_schema_org.json
        ├── student_scores.json
        ├── weather_telemetry.csv
        ├── author_quotes.txt
        ├── arcade_tournament_scores.csv
        ├── shipment_tracking_ids.json
        ├── gps_elevation_readings.json
        ├── server_audit_log.csv
        └── mixed_sensor_dump.json
```

## Quick Start

1. **Run the built-in classroom lessons and visual speed comparison:**
   ```bash
   python main.py
   ```

2. **Test your own JSON, CSV, or TXT file in class:**
   ```bash
   python main.py --file path/to/your_data.json
   ```

3. **Benchmark a sample custom sorting algorithm (`bubble`, `selection`, or `insertion`):**
   ```bash
   python main.py --file tests/data/weather_telemetry.csv --custom-algo bubble
   ```

4. **Run dataset unit tests and generate per-dataset CamelCase Markdown reports in `tests/results/`:**
   ```bash
   python main.py --runalltests
   ```

## Classroom Labs (`lessons/`)

Work through the guided labs in `lessons/` to practice Big O analysis, algorithm implementation, and automated schema discovery:

* **Lab 01 (`lessons/01_big_o_scavenger_hunt.md`):** Inspect real JSON, CSV, and TXT datasets via the CLI and compare how `smart_sort()` matches algorithms to data shapes.
* **Lab 02 (`lessons/02_custom_sort_starter.py`):** Implement your own `O(n log n)` Merge Sort in Python and race it against `O(n^2)` Bubble Sort and Python's built-in Timsort.
* **Lab 03 (`lessons/03_breaking_the_profiler.md`):** Design custom datasets to test threshold boundaries between Counting Sort, Timsort, and Bucket Sort.
* **Lab 04 (`lessons/04_schema_discovery_lab.md`):** Explore how statistical scoring automatically detects sort keys in nested JSON and CSV files without hardcoded column names.

## Big O Cheat Sheet

When `smart_sort()` prints a report, it displays the **Big O** time complexity of the winning algorithm. Use this quick reference to interpret how fast an algorithm scales as the number of records (`n`) grows:

| Big O | Name | Everyday Analogy | Speed as `n` Grows |
| :--- | :--- | :--- | :--- |
| **O(1)** | Constant Time | Checking if a single sticky note is in order. | Instant regardless of size. |
| **O(n)** | Linear Time | Reading every page of a book once from front to back. | Doubles if data doubles. |
| **O(n + k)** | Linear + Range (`k`) | Sorting exam scores (`0–50`) into labeled folders. | Very fast when the number range `k` is small. |
| **O(nk)** | Linear × Digits (`k`) | Sorting 9-digit barcodes one digit column at a time. | Fast for large sets of fixed-digit integers. |
| **O(n log n)** | Linearithmic Time | Splitting a shuffled deck into halves, sorting each half, and merging. | Gold standard for general-purpose sorting. |
| **O(n^2)** | Quadratic Time | Comparing every student in a room with every other student. | Slows down dramatically on large datasets. |

## Python API Usage (`src/smart_sorter.py`)

Students can import `smart_sort()` directly into their own Python scripts to sort lists, dictionaries, or custom objects with automatic Big O diagnostics:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
from smart_sorter import smart_sort

# 1. Automatic schema discovery & sorting on dictionary records
products = [
    {"name": "Keyboard", "offers": {"price": "79.99"}},
    {"name": "USB Cable", "offers": {"price": "9.99"}},
    {"name": "Mouse", "offers": {"price": "24.50"}},
]
sorted_products = smart_sort(products, explain=True)

# 2. Supplying a student-written custom sorting algorithm
def student_bubble_sort(paired_items, reverse=False):
    arr = list(paired_items)
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            should_swap = (arr[j] < arr[j + 1]) if reverse else (arr[j] > arr[j + 1])
            if should_swap:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return [orig for _, orig in arr]

custom_sorted = smart_sort(
    products,
    sort_key="offers.price",
    custom_sort_fn=student_bubble_sort,
    custom_sort_name="Student Bubble Sort",
    custom_big_o="O(n^2)",
    explain=True,
)
```

> **Note:** `smart_sort()` wraps items passed to `custom_sort_fn` in a `_ComparablePair` guard so comparing pairs directly (such as `arr[j] > arr[j + 1]`) compares only the extracted sort keys and never raises a `TypeError` on duplicate dictionary records.

## Testing Custom Student Datasets (`--file`)

Students can pass any `.json`, `.csv`, or `.txt` file into `main.py` using the `--file` (or `-f`) flag. `smart_sort()` will automatically discover the best sortable field, choose an algorithm, print the Big O report, display a preview of the sorted items, and save a formatted `.md` report inside `tests/results/`.

### CLI Options

| Flag | Short | Description | Example |
| :--- | :--- | :--- | :--- |
| `--file <path>` | `-f` | Path to a `.json`, `.csv`, or `.txt` file to inspect and sort. | `python main.py --file my_scores.csv` |
| `--key <field>` | `-k` | Optional column/field name or nested dotted path to override auto-detection. | `python main.py -f store.json -k offers.price` |
| `--reverse` | `-r` | Sort in descending order (highest to lowest / Z to A). | `python main.py -f my_scores.csv --reverse` |
| `--preview <n>` | `-p` | Number of sorted records to display after sorting (default: `5`). | `python main.py -f my_scores.csv --preview 10` |
| `--custom-algo <name>` | `-c` | Override auto-selection with a built-in classroom custom sort (`bubble`, `selection`, `insertion`). | `python main.py -f tests/data/weather_telemetry.csv -c insertion` |
| `--report-out <path>` | `-o` | Custom output file or directory path for generated Markdown reports (default: `tests/results/`). | `python main.py -f my_scores.csv -o tests/results/my_run.md` |
| `--runalltests` | — | Run dataset unit tests in `tests/` and write one `<DatasetName>.md` report per file in `tests/data/` into `tests/results/`. | `python main.py --runalltests` |

## Automated Per-Dataset Markdown Reports (`--runalltests`)

Running `python main.py --runalltests` discovers and runs dataset unit tests in `tests/` and saves one concise Markdown report per dataset in `tests/data/` into `tests/results/`. Each file is named in CamelCase with underscores removed using the pattern `<DatasetName>.md` (for example, `StudentScores.md` or `AuthorQuotes.md`) and begins with `# Test for <dataset_file>`. For non-built-in algorithms, the report also includes the external source URL and install command.

You can also pass specific test targets after `--runalltests` (which `main.py` forwards to `unittest`):

```bash
python main.py --runalltests TestSmartSorterClassroom.test_student_scores_counting_sort
```

## How `smart_sort()` Chooses an Algorithm

During a single O(n) inspection pass, `smart_sort()` profiles the dataset and selects the optimal sorting method:

| Chosen Sort Method | Big O | When `smart_sort()` Picks It |
| :--- | :--- | :--- |
| **Timsort / Powersort (Python Built-in)** | O(n) best / O(n log n) worst | Data is >= 85% ordered, or consists of general strings, uneven floats, or moderate-sized integers. |
| **Type-Safe Timsort (Python Built-in)** | O(n log n) | Dataset mixes incompatible or non-finite types (`None`, booleans, numbers, `NaN`/`Inf`, and strings), ranked cleanly without `TypeError`. |
| **No Sort Needed (Direct Return)** | O(1) | List has `0` or `1` item. |
| **Counting Sort** | O(n + k) | n >= 500 integers where the value spread k <= 2n (e.g., exam or arcade scores). |
| **Radix Sort** | O(nk) | n >= 50,000 non-negative integers with a wide numeric range (e.g., 8- or 9-digit IDs). |
| **Bucket Sort** | O(n + k) | n >= 25,000 finite floating-point numbers spread evenly across their range. |
| **Custom Algorithm** | User-defined | Student passes `custom_sort_fn` in Python or `--custom-algo` via CLI. |

## What `(see readme.md)` Means in the Output

When `smart_sort()` selects an algorithm that is **not built into Python's standard library**, it appends `(see readme.md)` to the report and includes an installation or reference link:

* **Built-In Methods (No Hint Shown):** `Timsort / Powersort`, `Type-Safe Timsort`, and `No Sort Needed` use Python's native `sorted()` or direct return and work with zero setup.
* **Counting, Radix, & Bucket Sort:** For standalone use outside this lab, these algorithms are available via `pip install sortcraft` ([PyPI](https://pypi.org/project/sortcraft/)).
* **Custom Algorithm:** Runs your own `custom_sort_fn` callback. See reference implementations at [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python/tree/master/sorts).

## Try It Yourself: Student Mini-Challenges

Run these commands in your terminal and compare the generated reports in `tests/results/`:

1. **Test Nearly Sorted Data:** Run `python main.py --file tests/data/server_audit_log.csv` and observe why Timsort achieves `O(n) best` time.
2. **Compare `O(n^2)` Algorithms:** Race Bubble Sort against Insertion Sort on the same file using `--custom-algo bubble` vs. `--custom-algo insertion`.
3. **Override Auto-Key Discovery:** Run `python main.py --file tests/data/weather_telemetry.csv` without `--key`, then re-run with `--key` set to a different column name.
4. **Inspect Mixed Data Types:** Run `python main.py --file tests/data/mixed_sensor_dump.json` to see how `Type-Safe Timsort` avoids Python's `TypeError` on `None`, numbers, and text.

## Key Terms Glossary

* **Cardinality:** The number of unique values in a column compared to the total number of rows. Higher cardinality usually makes a better sort key.
* **Nearly Sorted Runs:** Consecutive sections of a list that are already in ascending or descending order. Timsort detects these runs to skip unnecessary work.
* **Stable Sort:** A sorting algorithm that keeps records with equal keys in their original relative order.
* **Type Coercion:** Automatically converting numeric text like `"79.99"` into real numbers (`79.99`) so values sort numerically (`9.99` before `79.99`) instead of alphabetically.

## Troubleshooting Common Errors

* **`Unsupported file extension`:** Make sure your input file ends in `.json`, `.csv`, or `.txt`.
* **`JSON root is an object with no list of records`:** If your JSON file starts with `{ ... }`, make sure at least one top-level property holds a list `[ ... ]` of items to sort.
* **Sorting numbers alphabetically (`"100"` before `"20"`):** Check that values don't include currency symbols (`$`) or units (`kg`) inside the string, which prevents automatic numeric conversion.
