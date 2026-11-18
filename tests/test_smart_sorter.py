"""
tests/test_smart_sorter.py
Automated unit tests verifying algorithm selection, schema discovery,
custom algorithms, edge cases, CLI execution, and Markdown report generation.
"""

import csv
import io
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "tests" / "data"
RESULTS_DIR = PROJECT_ROOT / "tests" / "results"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from smart_sorter import (
    _ComparablePair,
    _SORT_METHOD_DECISION_MATRIX,
    _should_show_readme_hint,
    smart_sort,
)


class TestSmartSorterClassroom(unittest.TestCase):
    def _run_with_output(self, data, emit_report=True, dataset_file=None, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = smart_sort(data, explain=True, **kwargs)
        output = buf.getvalue()
        if output and emit_report:
            if dataset_file:
                sys.stdout.write(f"* Dataset File : {dataset_file}\n")
            sys.stdout.write(output)
        return result, output

    def test_readme_hint_decision_matrix(self):
        self.assertTrue(_should_show_readme_hint("Counting Sort"))
        self.assertTrue(_should_show_readme_hint("Radix Sort"))
        self.assertTrue(_should_show_readme_hint("Bucket Sort"))
        self.assertTrue(_should_show_readme_hint("Custom Algorithm"))
        self.assertTrue(_should_show_readme_hint("Custom Algorithm: Bubble Sort"))

        self.assertFalse(_should_show_readme_hint("Timsort / Powersort (Python Built-in)"))
        self.assertFalse(_should_show_readme_hint("Type-Safe Timsort (Python Built-in)"))
        self.assertFalse(_should_show_readme_hint("No Sort Needed (Direct Return)"))

        expected_methods = {
            "Timsort / Powersort (Python Built-in)",
            "Type-Safe Timsort (Python Built-in)",
            "No Sort Needed (Direct Return)",
            "Counting Sort",
            "Radix Sort",
            "Bucket Sort",
            "Custom Algorithm",
        }
        self.assertEqual(set(_SORT_METHOD_DECISION_MATRIX.keys()), expected_methods)

        for method, meta in _SORT_METHOD_DECISION_MATRIX.items():
            if meta["is_builtin"]:
                self.assertIsNone(meta["source_url"], msg=f"{method} should have source_url=None")
                self.assertIsNone(meta["install_cmd"], msg=f"{method} should have install_cmd=None")
            else:
                self.assertTrue(meta["source_url"].startswith("https://"), msg=f"{method} missing source_url")
                self.assertTrue(bool(meta["install_cmd"]), msg=f"{method} missing install_cmd")

    def test_comparable_pair_equality_and_ordering(self):
        p1 = _ComparablePair(10, {"id": "a"})
        p2 = _ComparablePair(10, {"id": "b"})
        p3 = _ComparablePair(20, {"id": "c"})

        self.assertTrue(p1 == p2)
        self.assertFalse(p1 != p2)
        self.assertTrue(p1 != p3)
        self.assertTrue(p1 < p3)
        self.assertTrue(p1 <= p2)
        self.assertTrue(p3 > p2)
        self.assertTrue(p2 >= p1)

    def test_custom_algorithm_execution_and_readme_hint(self):
        def student_selection_sort(paired_items, reverse=False):
            arr = list(paired_items)
            n = len(arr)
            for i in range(n):
                target_idx = i
                for j in range(i + 1, n):
                    if (arr[j] > arr[target_idx]) if reverse else (arr[j] < arr[target_idx]):
                        target_idx = j
                arr[i], arr[target_idx] = arr[target_idx], arr[i]
            return [orig for _, orig in arr]

        sample_items = [
            {"name": "Keyboard", "price": 79.99},
            {"name": "Mouse", "price": 24.50},
            {"name": "Monitor", "price": 199.00},
            {"name": "USB Cable", "price": 9.99},
            {"name": "Mousepad", "price": 24.50},
        ]

        result, output = self._run_with_output(
            sample_items,
            emit_report=False,
            sort_key="price",
            custom_sort_fn=student_selection_sort,
            custom_sort_name="Selection Sort",
            custom_big_o="O(n^2)",
        )

        self.assertEqual([item["price"] for item in result], [9.99, 24.50, 24.50, 79.99, 199.00])
        self.assertIn("* Chosen sort method should be: Custom Algorithm: Selection Sort (see readme.md)", output)
        self.assertIn("* Install / Source:", output)
        self.assertIn("https://github.com/TheAlgorithms/Python/tree/master/sorts", output)
        self.assertIn("* Big O: O(n^2)", output)

        result_rev, output_rev = self._run_with_output(
            [5, 1, 4, 2, 3],
            emit_report=False,
            reverse=True,
            custom_sort_fn=student_selection_sort,
        )
        self.assertEqual(result_rev, [5, 4, 3, 2, 1])
        self.assertIn("* Chosen sort method should be: Custom Algorithm (see readme.md)", output_rev)

    def test_uniform_floats_bucket_sort_and_verbose_labels(self):
        rng = random.Random(101)
        floats = [rng.uniform(0.0, 1000.0) for _ in range(60_000)]
        result, output = self._run_with_output(floats, emit_report=False)

        self.assertEqual(result, sorted(floats))
        self.assertIn("* number of records : 60_000", output)
        self.assertIn("* type = uniformly distributed floats", output)
        self.assertIn("* Chosen sort method should be: Bucket Sort (see readme.md)", output)
        self.assertIn("* Install / Source: pip install sortcraft (https://pypi.org/project/sortcraft/)", output)
        self.assertIn("* Big O: O(n + k)", output)

    def test_nan_and_infinity_floats_route_safely_to_type_safe_timsort(self):
        rng = random.Random(42)
        floats_with_nan = [rng.uniform(0.0, 100.0) for _ in range(30_000)]
        floats_with_nan[500] = float("nan")
        floats_with_nan[1000] = float("inf")
        floats_with_nan[1500] = float("-inf")

        result, output = self._run_with_output(floats_with_nan, emit_report=False)
        self.assertEqual(len(result), len(floats_with_nan))
        self.assertIn("Type-Safe Timsort (Python Built-in)", output)
        self.assertNotIn("* Install / Source:", output)
        self.assertTrue(math.isnan(result[-1]))

    def test_student_scores_counting_sort(self):
        with open(DATA_DIR / "student_scores.json", "r", encoding="utf-8") as f:
            records = json.load(f)

        result, output = self._run_with_output(
            records, dataset_file="student_scores.json", sort_key="pointsEarned"
        )
        self.assertEqual([r["pointsEarned"] for r in result], sorted(r["pointsEarned"] for r in records))
        self.assertIn("* number of records : 2_500", output)
        self.assertIn("* Chosen sort method should be: Counting Sort (see readme.md)", output)
        self.assertIn("* Install / Source: pip install sortcraft (https://pypi.org/project/sortcraft/)", output)
        self.assertIn("* Big O: O(n + k)", output)

    def test_large_barcodes_radix_sort(self):
        rng = random.Random(7)
        barcodes = [rng.randint(100_000_000, 999_999_999) for _ in range(60_000)]
        result, output = self._run_with_output(barcodes, emit_report=False)

        self.assertEqual(result, sorted(barcodes))
        self.assertIn("* Chosen sort method should be: Radix Sort (see readme.md)", output)
        self.assertIn("* Install / Source: pip install sortcraft (https://pypi.org/project/sortcraft/)", output)
        self.assertIn("* Big O: O(nk)", output)

    def test_schema_org_nested_string_price_coercion(self):
        with open(DATA_DIR / "products_schema_org.json", "r", encoding="utf-8") as f:
            items = json.load(f)

        result, output = self._run_with_output(
            items, dataset_file="products_schema_org.json", sort_key="offers.price"
        )
        prices = [float(x["offers"]["price"]) for x in result]
        self.assertEqual(prices, sorted(prices))
        self.assertIn("* Chosen sort method should be: Timsort / Powersort (Python Built-in)\n", output)
        self.assertNotIn("(see readme.md)", output)

    def test_standard_products_json_auto_discovery(self):
        with open(DATA_DIR / "products_standard.json", "r", encoding="utf-8") as f:
            items = json.load(f)

        result, _ = self._run_with_output(items, dataset_file="products_standard.json")
        self.assertEqual(len(result), len(items))

    def test_weather_csv_auto_discovery(self):
        with open(DATA_DIR / "weather_telemetry.csv", "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        result, _ = self._run_with_output(rows, dataset_file="weather_telemetry.csv")
        self.assertEqual(len(result), len(rows))

    def test_author_quotes_strings(self):
        with open(DATA_DIR / "author_quotes.txt", "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f if line.strip()]

        result, output = self._run_with_output(quotes, dataset_file="author_quotes.txt")
        self.assertEqual(result, sorted(quotes))
        self.assertIn("variable-length strings", output)
        self.assertNotIn("(see readme.md)", output)

    def test_nearly_sorted_runs_detection(self):
        nearly_sorted = list(range(1_000))
        nearly_sorted[500], nearly_sorted[501] = nearly_sorted[501], nearly_sorted[500]
        result, output = self._run_with_output(nearly_sorted, emit_report=False)

        self.assertEqual(result, list(range(1_000)))
        self.assertIn("nearly sorted", output)
        self.assertIn("O(n) best", output)
        self.assertNotIn("(see readme.md)", output)

    def test_mixed_types_numeric_ordering(self):
        messy = [100, "apple", None, 20, "banana", -5, 3.14]
        result, output = self._run_with_output(messy, emit_report=False)
        self.assertEqual(result, [None, -5, 3.14, 20, 100, "apple", "banana"])
        self.assertIn("Type-Safe Timsort", output)
        self.assertNotIn("(see readme.md)", output)

    def test_empty_and_single_element(self):
        result_empty, output_empty = self._run_with_output([], emit_report=False)
        self.assertEqual(result_empty, [])
        self.assertIn("No Sort Needed (Direct Return)", output_empty)
        self.assertNotIn("(see readme.md)", output_empty)
        self.assertEqual(smart_sort([99]), [99])

    # --- Tests for the 5 newly added datasets in tests/data/ ---

    def test_arcade_tournament_scores_csv_counting_sort(self):
        filepath = DATA_DIR / "arcade_tournament_scores.csv"
        if not filepath.is_file():
            self.skipTest("arcade_tournament_scores.csv not present in tests/data/")

        with open(filepath, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        result, output = self._run_with_output(
            rows, dataset_file="arcade_tournament_scores.csv", sort_key="points"
        )
        points = [int(r["points"]) for r in result]
        self.assertEqual(points, sorted(points))
        self.assertIn("* Chosen sort method should be: Counting Sort (see readme.md)", output)
        self.assertIn("* Big O: O(n + k)", output)

    def test_shipment_tracking_ids_json_radix_sort(self):
        filepath = DATA_DIR / "shipment_tracking_ids.json"
        if not filepath.is_file():
            self.skipTest("shipment_tracking_ids.json not present in tests/data/")

        with open(filepath, "r", encoding="utf-8") as f:
            tracking_ids = json.load(f)

        result, output = self._run_with_output(tracking_ids, dataset_file="shipment_tracking_ids.json")
        self.assertEqual(result, sorted(tracking_ids))
        self.assertIn("* Chosen sort method should be: Radix Sort (see readme.md)", output)
        self.assertIn("* Big O: O(nk)", output)

    def test_gps_elevation_readings_json_bucket_sort(self):
        filepath = DATA_DIR / "gps_elevation_readings.json"
        if not filepath.is_file():
            self.skipTest("gps_elevation_readings.json not present in tests/data/")

        with open(filepath, "r", encoding="utf-8") as f:
            readings = json.load(f)

        result, output = self._run_with_output(
            readings, dataset_file="gps_elevation_readings.json", sort_key="elevation_m"
        )
        elevations = [float(r["elevation_m"]) for r in result]
        self.assertEqual(elevations, sorted(elevations))
        self.assertIn("* Chosen sort method should be: Bucket Sort (see readme.md)", output)
        self.assertIn("* Big O: O(n + k)", output)

    def test_server_audit_log_csv_nearly_sorted_timsort(self):
        filepath = DATA_DIR / "server_audit_log.csv"
        if not filepath.is_file():
            self.skipTest("server_audit_log.csv not present in tests/data/")

        with open(filepath, "r", encoding="utf-8", newline="") as f:
            logs = list(csv.DictReader(f))

        result, output = self._run_with_output(
            logs, dataset_file="server_audit_log.csv", sort_key="timestamp"
        )
        timestamps = [r["timestamp"] for r in result]
        self.assertEqual(timestamps, sorted(timestamps))
        self.assertIn("nearly sorted", output)
        self.assertIn("Timsort / Powersort (Python Built-in)", output)
        self.assertNotIn("(see readme.md)", output)

    def test_mixed_sensor_dump_json_type_safe_timsort(self):
        filepath = DATA_DIR / "mixed_sensor_dump.json"
        if not filepath.is_file():
            self.skipTest("mixed_sensor_dump.json not present in tests/data/")

        with open(filepath, "r", encoding="utf-8") as f:
            messy_data = json.load(f)

        result, output = self._run_with_output(messy_data, dataset_file="mixed_sensor_dump.json")
        self.assertEqual(len(result), len(messy_data))
        self.assertIn("mixed / heterogeneous data types", output)
        self.assertIn("Type-Safe Timsort (Python Built-in)", output)
        self.assertNotIn("(see readme.md)", output)

    # --- End-to-End CLI Tests for main.py --file, --custom-algo, --runalltests, & Markdown Reports ---

    def test_cli_file_custom_algo_and_markdown_report(self):
        main_script = PROJECT_ROOT / "main.py"
        weather_file = DATA_DIR / "weather_telemetry.csv"
        if not main_script.is_file() or not weather_file.is_file():
            self.skipTest("main.py or weather_telemetry.csv not present")

        with tempfile.TemporaryDirectory() as tmpdir:
            report_a = Path(tmpdir) / "auto_report.md"
            proc_auto = subprocess.run(
                [
                    sys.executable,
                    str(main_script),
                    "--file",
                    str(weather_file),
                    "--preview",
                    "2",
                    "--report-out",
                    str(report_a),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_auto.returncode, 0, msg=proc_auto.stderr)
            self.assertIn("[smart_sort Classroom Report]", proc_auto.stdout)
            self.assertIn("[Report Saved]", proc_auto.stdout)
            self.assertTrue(report_a.is_file())
            md_text_a = report_a.read_text(encoding="utf-8")
            self.assertIn("# Smart Sorter Inspection Report: weather_telemetry.csv", md_text_a)
            self.assertIn("#### Classroom Diagnostic Report", md_text_a)
            self.assertIn("- **type:** JSON / dictionary records", md_text_a)
            self.assertIn("#### Preview: First 2 of", md_text_a)

            report_b = Path(tmpdir) / "custom_report.md"
            proc_custom = subprocess.run(
                [
                    sys.executable,
                    str(main_script),
                    "--file",
                    str(weather_file),
                    "--custom-algo",
                    "insertion",
                    "--reverse",
                    "--preview",
                    "3",
                    "--report-out",
                    str(report_b),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_custom.returncode, 0, msg=proc_custom.stderr)
            self.assertIn("Custom Algorithm: Insertion Sort (see readme.md)", proc_custom.stdout)
            self.assertIn("* Big O: O(n) best / O(n^2) worst", proc_custom.stdout)
            self.assertTrue(report_b.is_file())
            md_text_b = report_b.read_text(encoding="utf-8")
            self.assertIn("- **Big O:** O(n) best / O(n^2) worst", md_text_b)

    def test_cli_runalltests_generates_camel_case_reports(self):
        main_script = PROJECT_ROOT / "main.py"
        if not main_script.is_file():
            self.skipTest("main.py not present")

        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(main_script),
                    "--runalltests",
                    "--report-out",
                    tmpdir,
                    "TestSmartSorterClassroom.test_author_quotes_strings",
                    "TestSmartSorterClassroom.test_student_scores_counting_sort",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("[PASS   ] test_author_quotes_strings", proc.stdout)
            self.assertIn("[PASS   ] test_student_scores_counting_sort", proc.stdout)
            self.assertNotIn("AuthorQuotes.md", proc.stdout)

            builtin_file = Path(tmpdir) / "AuthorQuotes.md"
            self.assertTrue(builtin_file.is_file())
            builtin_content = builtin_file.read_text(encoding="utf-8")
            self.assertIn("# Test for author_quotes.txt", builtin_content)
            self.assertIn("- **Best Sort Chosen:** Timsort / Powersort (Python Built-in)", builtin_content)
            self.assertIn("- **Why:**", builtin_content)
            self.assertNotIn("Source URL", builtin_content)

            non_builtin_file = Path(tmpdir) / "StudentScores.md"
            self.assertTrue(non_builtin_file.is_file())
            non_builtin_content = non_builtin_file.read_text(encoding="utf-8")
            self.assertIn("# Test for student_scores.json", non_builtin_content)
            self.assertIn("- **Best Sort Chosen:** Counting Sort", non_builtin_content)
            self.assertIn("- **Source URL:** https://pypi.org/project/sortcraft/", non_builtin_content)
            self.assertIn("- **Install:** `pip install sortcraft`", non_builtin_content)

    def test_cli_missing_file_exits_cleanly(self):
        main_script = PROJECT_ROOT / "main.py"
        if not main_script.is_file():
            self.skipTest("main.py not present")

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_report = Path(tmpdir) / "error_report.md"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(main_script),
                    "--file",
                    "nonexistent_student_data.json",
                    "--report-out",
                    str(missing_report),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("[Error] Could not find file:", proc.stdout)
            self.assertTrue(missing_report.is_file())
            self.assertIn("> **Error:** Could not find file:", missing_report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
