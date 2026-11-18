"""
Lesson 2: Build & Benchmark Your Own Sorting Algorithm
10th-Grade Computer Science Lab

Instructions:
1. Complete the `student_merge_sort` function below without using Python's built-in
   `sorted()` or `.sort()`.
2. Run this script from the project root:
       python lessons/02_custom_sort_starter.py
3. Compare your Merge Sort's runtime against Bubble Sort and Python's built-in Timsort!
"""

from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from main import bubble_sort_paired
from smart_sorter import smart_sort


def student_merge_sort(paired_items, reverse=False):
    """
    Recursive O(n log n) Merge Sort over `_ComparablePair` items.

    Remember:
    - Each element in `paired_items` is a `_ComparablePair(key, original_record)`.
    - Comparing two elements directly (e.g., `left[i] <= right[j]`) compares ONLY
      their keys, so duplicate keys with dictionary records will never crash!
    - Return a flat list of `original_record` objects (or `_ComparablePair` items,
      which `smart_sort` automatically unwraps).
    """
    arr = list(paired_items)

    def _merge_sort(sublist):
        # Base case: a list of 0 or 1 items is already sorted
        if len(sublist) <= 1:
            return sublist

        mid = len(sublist) // 2
        left_half = _merge_sort(sublist[:mid])
        right_half = _merge_sort(sublist[mid:])

        return _merge(left_half, right_half)

    def _merge(left, right):
        merged = []
        i = 0
        j = 0

        # TODO: Compare left[i] and right[j] while both indices are in bounds.
        # Hint: If `reverse` is True, pick the larger element first (`left[i] >= right[j]`).
        #       If `reverse` is False, pick the smaller element first (`left[i] <= right[j]`).
        while i < len(left) and j < len(right):
            if (left[i] >= right[j]) if reverse else (left[i] <= right[j]):
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1

        # Append any remaining items from left or right
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged

    sorted_pairs = _merge_sort(arr)
    return [orig for _, orig in sorted_pairs]


def main():
    rng = random.Random(42)
    sample_records = [
        {"student": f"Student-{i:04d}", "score": rng.randint(0, 100)}
        for i in range(3_000)
    ]

    print("=" * 68)
    print("  LESSON 2: RACING BUBBLE SORT vs. YOUR MERGE SORT vs. TIMSORT")
    print("=" * 68)

    # 1. Verify correctness on a small ascending and descending check
    small_test = [{"id": 1, "val": 30}, {"id": 2, "val": 10}, {"id": 3, "val": 20}, {"id": 4, "val": 10}]
    asc = smart_sort(small_test, sort_key="val", custom_sort_fn=student_merge_sort)
    desc = smart_sort(small_test, sort_key="val", reverse=True, custom_sort_fn=student_merge_sort)
    assert [x["val"] for x in asc] == [10, 10, 20, 30], "Ascending sort failed!"
    assert [x["val"] for x in desc] == [30, 20, 10, 10], "Descending sort failed!"
    print("[PASS] Small correctness & stability check passed!\n")

    # 2. Race O(n^2) Bubble Sort
    print("--- Race 1: Bubble Sort O(n^2) ---")
    bubble_res = smart_sort(
        sample_records,
        sort_key="score",
        custom_sort_fn=bubble_sort_paired,
        custom_sort_name="Bubble Sort",
        custom_big_o="O(n^2)",
        explain=True,
    )

    # 3. Race Student O(n log n) Merge Sort
    print("\n--- Race 2: Student Merge Sort O(n log n) ---")
    merge_res = smart_sort(
        sample_records,
        sort_key="score",
        custom_sort_fn=student_merge_sort,
        custom_sort_name="Student Merge Sort",
        custom_big_o="O(n log n)",
        explain=True,
    )

    # 4. Race Built-in C Timsort
    print("\n--- Race 3: Built-in Adaptive smart_sort() ---")
    smart_res = smart_sort(sample_records, sort_key="score", explain=True)

    assert [x["score"] for x in bubble_res] == [x["score"] for x in merge_res] == [x["score"] for x in smart_res]
    print("\n[SUCCESS] All three algorithms produced the exact same sorted order!")


if __name__ == "__main__":
    main()
