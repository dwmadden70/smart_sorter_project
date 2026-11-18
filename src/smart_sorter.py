"""
smart_sorter.py
Universal Adaptive Sorting Helper Module (Classroom Edition)

Inspects unknown input types and shapes at runtime, profiles data distributions
in a single O(n) pass, selects the optimal Big O sorting algorithm, and prints
student-friendly classroom explanations with wall-clock timing in seconds.
"""

from itertools import chain
import math
import re
import time

_NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$")
_URL_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)

# Decision matrix mapping each sorting method to whether it is non-built-in,
# requires the "(see readme.md)" guidance note, and where it can be found/installed.
_SORT_METHOD_DECISION_MATRIX = {
    "No Sort Needed (Direct Return)": {
        "is_builtin": True,
        "show_readme_hint": False,
        "source_url": None,
        "install_cmd": None,
    },
    "Timsort / Powersort (Python Built-in)": {
        "is_builtin": True,
        "show_readme_hint": False,
        "source_url": None,
        "install_cmd": None,
    },
    "Type-Safe Timsort (Python Built-in)": {
        "is_builtin": True,
        "show_readme_hint": False,
        "source_url": None,
        "install_cmd": None,
    },
    "Counting Sort": {
        "is_builtin": False,
        "show_readme_hint": True,
        "source_url": "https://pypi.org/project/sortcraft/",
        "install_cmd": "pip install sortcraft",
    },
    "Radix Sort": {
        "is_builtin": False,
        "show_readme_hint": True,
        "source_url": "https://pypi.org/project/sortcraft/",
        "install_cmd": "pip install sortcraft",
    },
    "Bucket Sort": {
        "is_builtin": False,
        "show_readme_hint": True,
        "source_url": "https://pypi.org/project/sortcraft/",
        "install_cmd": "pip install sortcraft",
    },
    "Custom Algorithm": {
        "is_builtin": False,
        "show_readme_hint": True,
        "source_url": "https://github.com/TheAlgorithms/Python/tree/master/sorts",
        "install_cmd": "User-defined callback via custom_sort_fn (reference implementations: https://github.com/TheAlgorithms/Python/tree/master/sorts)",
    },
}


class _ComparablePair:
    """
    Tuple-unwrapping guard for student custom_sort_fn callbacks.
    Behaves like a 2-tuple (key, original_item) when unpacked or indexed,
    but restricts ==, !=, <, <=, >, >= comparisons strictly to pair[0] (the key)
    so duplicate keys with unorderable records (e.g., dicts) never raise TypeError.
    """

    __slots__ = ("key", "original")

    def __init__(self, key, original):
        self.key = key
        self.original = original

    def __getitem__(self, idx):
        if idx == 0:
            return self.key
        if idx == 1:
            return self.original
        raise IndexError("tuple index out of range")

    def __iter__(self):
        yield self.key
        yield self.original

    def __len__(self):
        return 2

    def _extract_other_key(self, other):
        if isinstance(other, _ComparablePair):
            return other.key
        if isinstance(other, tuple) and len(other) > 0:
            return other[0]
        return other

    def __eq__(self, other):
        return self.key == self._extract_other_key(other)

    def __ne__(self, other):
        return self.key != self._extract_other_key(other)

    def __lt__(self, other):
        return self.key < self._extract_other_key(other)

    def __le__(self, other):
        return self.key <= self._extract_other_key(other)

    def __gt__(self, other):
        return self.key > self._extract_other_key(other)

    def __ge__(self, other):
        return self.key >= self._extract_other_key(other)

    def __repr__(self):
        return f"({self.key!r}, {self.original!r})"


def _get_matrix_entry(chosen_method):
    """Returns the decision matrix metadata dictionary for chosen_method."""
    if chosen_method.startswith("Custom Algorithm"):
        return _SORT_METHOD_DECISION_MATRIX["Custom Algorithm"]
    return _SORT_METHOD_DECISION_MATRIX.get(chosen_method)


def _should_show_readme_hint(chosen_method):
    """Looks up whether chosen_method requires '(see readme.md)' via the decision matrix."""
    entry = _get_matrix_entry(chosen_method)
    if entry is not None:
        return entry["show_readme_hint"]
    return "(Python Built-in)" not in chosen_method


def _normalize_value(val):
    """Converts numeric strings like '79.99' or '42' into real int/float values."""
    if isinstance(val, str):
        stripped = val.strip()
        if _NUM_RE.match(stripped):
            return float(stripped) if "." in stripped else int(stripped)
    return val


def _extract_nested_value(obj, dotted_path):
    """Safely retrieves a nested dictionary value using dot notation (e.g., 'offers.price')."""
    curr = obj
    for part in dotted_path.split("."):
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            return None
    return curr


def _flatten_scalars(obj, prefix="", max_depth=3):
    """Flattens nested dictionaries up to max_depth into {dotted_path: scalar_value}."""
    result = {}
    if max_depth <= 0 or not isinstance(obj, dict):
        return result

    for k, v in obj.items():
        path = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            result.update(_flatten_scalars(v, prefix=path, max_depth=max_depth - 1))
        elif isinstance(v, (int, float, str, bool)) and v is not None:
            result[path] = v
    return result


def _score_candidate_field(path, values, sample_size):
    """
    Scores a dictionary field statistically without relying on domain-specific names.
    Combines completeness, data type fitness, cardinality (variance), and structure.
    """
    non_null = [v for v in values if v is not None and v != ""]
    if not non_null:
        return -1.0

    completeness = len(non_null) / sample_size
    if completeness < 0.5:
        return -1.0

    normalized = [_normalize_value(v) for v in non_null]
    unique_count = len(set(str(v) for v in normalized))

    if unique_count <= 1 and len(normalized) > 1:
        return 0.0

    cardinality_ratio = unique_count / len(normalized)

    num_count = sum(
        1
        for v in normalized
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    )
    bool_count = sum(1 for v in normalized if isinstance(v, bool))
    str_values = [v for v in normalized if isinstance(v, str)]

    if num_count == len(normalized):
        type_score = 1.0
    elif str_values and all(_ISO_DATE_RE.match(s.strip()) for s in str_values):
        type_score = 0.95
    elif bool_count == len(normalized):
        type_score = 0.20
    elif str_values:
        avg_len = sum(len(s) for s in str_values) / len(str_values)
        if any(_URL_RE.match(s.strip()) for s in str_values):
            type_score = 0.25
        elif avg_len <= 24:
            type_score = 0.80
        elif avg_len <= 60:
            type_score = 0.55
        else:
            type_score = 0.30
    else:
        type_score = 0.40

    depth = path.count(".")
    depth_penalty = depth * 0.05
    leaf = path.split(".")[-1].lower()
    hint_bonus = 0.08 if any(leaf.endswith(suf) for suf in ("id", "_at", "date", "time", "code", "num", "seq")) else 0.0

    score = (0.35 * completeness) + (0.35 * type_score) + (0.30 * cardinality_ratio) - depth_penalty + hint_bonus
    return round(score, 4)


def _discover_best_key(sample):
    """Automatically selects the best sortable field path from unknown JSON/dict objects."""
    flattened_rows = [_flatten_scalars(item) for item in sample if isinstance(item, dict)]
    if not flattened_rows:
        return None

    all_paths = set()
    for row in flattened_rows:
        all_paths.update(row.keys())

    best_path = None
    best_score = -1.0
    sample_size = len(flattened_rows)

    for path in sorted(all_paths):
        values = [row.get(path) for row in flattened_rows]
        score = _score_candidate_field(path, values, sample_size)
        if score > best_score:
            best_score = score
            best_path = path

    return best_path if best_score > 0 else None


def _is_uniformly_distributed(keys, min_val, max_val):
    """
    Checks in O(n) whether finite numeric values are spread evenly enough for Bucket Sort.
    Time Complexity: O(n) single pass across 10 decile bins.
    Space Complexity: O(1) fixed 10-element frequency list.
    """
    if not (math.isfinite(min_val) and math.isfinite(max_val)):
        return False

    span = max_val - min_val
    if not math.isfinite(span) or span <= 0 or len(keys) < 20:
        return False

    deciles = [0] * 10
    for k in keys:
        if not math.isfinite(k):
            return False
        idx = min(int(((k - min_val) / span) * 10), 9)
        deciles[idx] += 1

    expected = len(keys) / 10.0
    non_empty_bins = sum(1 for count in deciles if count > 0)
    max_bin_ratio = max(deciles) / expected
    return non_empty_bins >= 7 and max_bin_ratio <= 2.5


def _counting_sort_keyed(paired_items, min_val, max_val, reverse=False):
    """
    Stable O(n + k) Counting Sort that keeps full objects attached to integer keys.
    Time Complexity: O(n + k), where k = max_val - min_val + 1.
    Space Complexity: O(n + k) auxiliary bucket storage.
    """
    buckets = [[] for _ in range(max_val - min_val + 1)]
    for key, original in paired_items:
        buckets[key - min_val].append(original)

    ordered_buckets = reversed(buckets) if reverse else buckets
    return list(chain.from_iterable(ordered_buckets))


def _radix_sort_keyed(paired_items, max_val, reverse=False):
    """
    Stable O(nk) Radix Sort for large non-negative integer datasets.
    Time Complexity: O(n * d), where d is the number of base-10 digits in max_val.
    Space Complexity: O(n + 10) auxiliary digit buckets per pass.
    """
    exp = 1
    items = list(paired_items)
    while max_val // exp > 0:
        buckets = [[] for _ in range(10)]
        for pair in items:
            digit = (pair[0] // exp) % 10
            buckets[digit].append(pair)
        items = list(chain.from_iterable(buckets))
        exp *= 10

    result = [orig for _, orig in items]
    return list(reversed(result)) if reverse else result


def _bucket_sort_keyed(paired_items, min_val, max_val, reverse=False):
    """
    O(n + k) Bucket Sort for uniformly distributed finite floating-point numbers.
    Time Complexity: O(n) average when values are uniformly distributed; O(n log n) worst-case.
    Space Complexity: O(n) auxiliary scatter buckets.
    """
    n = len(paired_items)
    span = max_val - min_val
    if span == 0:
        return [orig for _, orig in paired_items]

    buckets = [[] for _ in range(n)]
    for key, original in paired_items:
        idx = min(int(((key - min_val) / span) * (n - 1)), n - 1)
        buckets[idx].append((key, original))

    result = []
    bucket_iter = reversed(buckets) if reverse else buckets
    for bucket in bucket_iter:
        bucket.sort(key=lambda pair: pair[0], reverse=reverse)
        result.extend(orig for _, orig in bucket)
    return result


def _type_safe_sort_key(pair):
    """
    Provides deterministic, crash-free ordering across heterogeneous data types
    while preserving true numeric ordering for ints and floats.
    Rank order: None (0) < bool (1) < finite numbers (2) < -Inf (3, 0) < +Inf (3, 1) < NaN (3, 2) < str (4) < other (5).
    """
    val = pair[0]
    if val is None:
        return (0, 0, "")
    if isinstance(val, bool):
        return (1, int(val), "")
    if isinstance(val, (int, float)):
        if math.isnan(val):
            return (3, 2, "")
        if math.isinf(val):
            return (3, 0 if val < 0 else 1, "")
        return (2, float(val), "")
    if isinstance(val, str):
        return (4, 0, val)
    return (5, 0, f"{type(val).__name__}:{val!r}")


def _estimate_time_bounds_seconds(n, big_o_label, actual_seconds):
    """
    Calculates projected best-case and worst-case time bounds in seconds
    for 10th-grade classroom comparison alongside actual runtime.
    """
    safe_actual = max(actual_seconds, 0.000001)
    log_factor = max(math.log2(max(n, 2)), 1.0)

    if big_o_label == "O(n + k)":
        min_sec = safe_actual * 0.80
        max_sec = safe_actual * (log_factor * 0.45)
    elif big_o_label == "O(nk)":
        min_sec = safe_actual * 0.85
        max_sec = safe_actual * 1.40
    elif "O(n) best" in big_o_label:
        min_sec = safe_actual * 0.75
        max_sec = safe_actual * log_factor
    else:
        min_sec = safe_actual / log_factor
        max_sec = safe_actual * 1.35

    min_sec = min(min_sec, safe_actual)
    max_sec = max(max_sec, safe_actual)
    return min_sec, max_sec


def _format_classroom_report(
    n,
    data_type_desc,
    discovered_key,
    chosen_method,
    big_o,
    min_sec,
    max_sec,
    actual_sec,
    reason,
):
    """Builds the student-friendly bulleted diagnostic output required for classroom use."""
    key_note = f" (auto-detected sort field: '{discovered_key}')" if discovered_key else ""
    readme_suffix = " (see readme.md)" if _should_show_readme_hint(chosen_method) else ""
    lines = [
        "[smart_sort Classroom Report]",
        f"* number of records : {n:_}",
        f"* type = {data_type_desc}{key_note}",
        f"* Chosen sort method should be: {chosen_method}{readme_suffix}",
    ]

    entry = _get_matrix_entry(chosen_method)
    if entry and not entry["is_builtin"]:
        source_url = entry.get("source_url")
        install_cmd = entry.get("install_cmd")
        if install_cmd and source_url and source_url not in install_cmd:
            lines.append(f"* Install / Source: {install_cmd} ({source_url})")
        elif install_cmd:
            lines.append(f"* Install / Source: {install_cmd}")
        elif source_url:
            lines.append(f"* Install / Source: {source_url}")

    lines.extend(
        [
            f"* Big O: {big_o}",
            f"* Time to sort: Min {min_sec:.4f} sec and Max of {max_sec:.4f} seconds (Actual: {actual_sec:.4f} seconds)",
            f"* Why this won: {reason}",
        ]
    )
    return "\n".join(lines)


def _unwrap_custom_result(raw_result, guarded_pairs):
    """
    Normalizes the return value of a student's custom_sort_fn into a flat list of
    original records, whether the student returned:
      1. A list of _ComparablePair objects
      2. A list of (key, original_record) tuples
      3. A list of original records directly
    """
    if not raw_result:
        return []

    first = raw_result[0]
    if isinstance(first, _ComparablePair):
        return [item.original for item in raw_result]

    if isinstance(first, tuple) and len(first) == 2:
        original_ids = {id(pair.original) for pair in guarded_pairs}
        if id(first[1]) in original_ids:
            return [orig for _, orig in raw_result]

    return list(raw_result)


def smart_sort(
    data,
    sort_key=None,
    key_fn=None,
    custom_sort_fn=None,
    custom_sort_name=None,
    custom_big_o="Custom / User-Defined",
    reverse=False,
    explain=False,
):
    """
    Universal adaptive sorting function.

    Parameters:
        data (iterable): Any list or iterable of numbers, strings, tuples, or dicts.
        sort_key (str, optional): Explicit dictionary key or dotted path (e.g., 'offers.price').
        key_fn (callable, optional): Custom function to extract sort keys from items.
        custom_sort_fn (callable, optional): Student-supplied custom sorting function
            accepting (paired_items, reverse=...) or (items, key=..., reverse=...).
            Uses _ComparablePair tuple-unwrapping guard so comparing pairs directly
            (e.g., arr[j] < arr[j + 1]) compares only keys and never crashes on duplicate
            dictionary records.
        custom_sort_name (str, optional): Display label for custom_sort_fn in reports.
        custom_big_o (str, optional): Big O complexity label for custom_sort_fn.
        reverse (bool): Sort descending if True (default False).
        explain (bool): Print verbose 10th-grade classroom breakdown if True.

    Returns:
        list: A newly sorted list of the original items.
    """
    start_time = time.perf_counter()
    items = list(data)
    n = len(items)

    if n <= 1:
        elapsed = time.perf_counter() - start_time
        if explain:
            print(
                _format_classroom_report(
                    n=n,
                    data_type_desc="trivial list (0 or 1 item)",
                    discovered_key=sort_key,
                    chosen_method="No Sort Needed (Direct Return)",
                    big_o="O(1)",
                    min_sec=elapsed,
                    max_sec=elapsed,
                    actual_sec=elapsed,
                    reason="A list with 0 or 1 item is already in order without doing any comparisons.",
                )
            )
        return items

    discovered_key = None
    is_dict_collection = all(isinstance(x, dict) for x in items)

    if key_fn is not None:
        paired = [(_normalize_value(key_fn(item)), item) for item in items]
        data_label_prefix = "custom-keyed objects"
    elif is_dict_collection:
        discovered_key = sort_key or _discover_best_key(items[: min(n, 50)])
        if not discovered_key:
            raise ValueError("smart_sort could not auto-detect a sortable field; pass sort_key or key_fn.")
        paired = [(_normalize_value(_extract_nested_value(item, discovered_key)), item) for item in items]
        data_label_prefix = "JSON / dictionary records"
    else:
        paired = [(_normalize_value(item), item) for item in items]
        data_label_prefix = ""

    if custom_sort_fn is not None:
        fn_name = getattr(custom_sort_fn, "__name__", "custom_sort_fn")
        if custom_sort_name:
            if custom_sort_name == "Custom Algorithm" or custom_sort_name.startswith("Custom Algorithm"):
                chosen_method = custom_sort_name
            else:
                chosen_method = f"Custom Algorithm: {custom_sort_name}"
        else:
            chosen_method = "Custom Algorithm"
        big_o = custom_big_o
        data_type_desc = f"{data_label_prefix or 'custom-sorted items'}"
        reason = f"Student-supplied custom sorting function '{fn_name}' was explicitly requested."

        guarded_pairs = [_ComparablePair(k, orig) for k, orig in paired]

        try:
            raw_sorted = custom_sort_fn(guarded_pairs, reverse=reverse)
        except TypeError:
            try:
                raw_sorted = custom_sort_fn(guarded_pairs)
                if reverse:
                    raw_sorted = list(reversed(raw_sorted))
            except TypeError:
                raw_sorted = custom_sort_fn(
                    items,
                    key=lambda item: _normalize_value(
                        key_fn(item)
                        if key_fn is not None
                        else (_extract_nested_value(item, discovered_key) if discovered_key else item)
                    ),
                    reverse=reverse,
                )

        sorted_result = _unwrap_custom_result(raw_sorted, guarded_pairs)

        actual_sec = time.perf_counter() - start_time
        if explain:
            min_sec, max_sec = _estimate_time_bounds_seconds(n, "O(n log n)", actual_sec)
            print(
                _format_classroom_report(
                    n=n,
                    data_type_desc=data_type_desc,
                    discovered_key=discovered_key,
                    chosen_method=chosen_method,
                    big_o=big_o,
                    min_sec=min_sec,
                    max_sec=max_sec,
                    actual_sec=actual_sec,
                    reason=reason,
                )
            )
        return sorted_result

    keys = [k for k, _ in paired]
    all_ints = all(isinstance(k, int) and not isinstance(k, bool) for k in keys)
    all_finite_nums = all(
        isinstance(k, (int, float)) and not isinstance(k, bool) and math.isfinite(k)
        for k in keys
    )
    all_strs = all(isinstance(k, str) for k in keys)

    comparable = all_finite_nums or all_strs
    in_order_ratio = 0.0
    if comparable:
        if reverse:
            in_order = sum(1 for i in range(n - 1) if keys[i] >= keys[i + 1])
        else:
            in_order = sum(1 for i in range(n - 1) if keys[i] <= keys[i + 1])
        in_order_ratio = in_order / (n - 1)

    chosen_method = ""
    big_o = ""
    data_type_desc = ""
    reason = ""
    sorted_result = None

    if comparable and in_order_ratio >= 0.85 and n >= 20:
        pct = int(round(in_order_ratio * 100))
        base_type = "integers" if all_ints else ("floats" if all_finite_nums else "strings")
        data_type_desc = f"nearly sorted {data_label_prefix or base_type} ({pct}% already in order)"
        chosen_method = "Timsort / Powersort (Python Built-in)"
        big_o = "O(n) best / O(n log n) worst"
        reason = f"Because {pct}% of adjacent records are already ordered, Python's built-in Timsort detects existing runs and finishes in near-linear time."
        sorted_result = [orig for _, orig in sorted(paired, key=lambda p: p[0], reverse=reverse)]

    elif all_ints:
        min_val, max_val = min(keys), max(keys)
        value_range = max_val - min_val

        if value_range <= n * 2 and n >= 500:
            data_type_desc = f"bounded integers in range [{min_val}, {max_val}]"
            if data_label_prefix:
                data_type_desc = f"{data_label_prefix} keyed by {data_type_desc}"
            chosen_method = "Counting Sort"
            big_o = "O(n + k)"
            reason = f"The spread of numbers (k = {value_range:_}) is small compared to the {n:_} records, so tallying counts in buckets avoids slow item-by-item comparisons."
            sorted_result = _counting_sort_keyed(paired, min_val, max_val, reverse=reverse)

        elif min_val >= 0 and n >= 50_000:
            digits = len(str(max_val))
            data_type_desc = f"large non-negative integers ({digits} digits max)"
            if data_label_prefix:
                data_type_desc = f"{data_label_prefix} keyed by {data_type_desc}"
            chosen_method = "Radix Sort"
            big_o = "O(nk)"
            reason = f"With {n:_} records and a wide number range, sorting digit-by-digit across k = {digits} digits beats O(n log n) comparison sorting."
            sorted_result = _radix_sort_keyed(paired, max_val, reverse=reverse)

        else:
            data_type_desc = f"general integers in range [{min_val}, {max_val}]"
            if data_label_prefix:
                data_type_desc = f"{data_label_prefix} keyed by {data_type_desc}"
            chosen_method = "Timsort / Powersort (Python Built-in)"
            big_o = "O(n log n)"
            reason = "For moderate-sized or wide-range integer lists, Python's compiled C Timsort runs faster than pure-Python bucket allocation."
            sorted_result = [orig for _, orig in sorted(paired, key=lambda p: p[0], reverse=reverse)]

    elif all_finite_nums:
        min_val, max_val = min(keys), max(keys)
        if n >= 25_000 and _is_uniformly_distributed(keys, min_val, max_val):
            data_type_desc = "uniformly distributed floats"
            if data_label_prefix:
                data_type_desc = f"{data_label_prefix} keyed by {data_type_desc}"
            chosen_method = "Bucket Sort"
            big_o = "O(n + k)"
            reason = f"The decimal values are spread evenly across [{min_val:.2f}, {max_val:.2f}], allowing Bucket Sort to scatter items into equal bins in linear average time."
            sorted_result = _bucket_sort_keyed(paired, min_val, max_val, reverse=reverse)
        else:
            data_type_desc = "floating-point numbers"
            if data_label_prefix:
                data_type_desc = f"{data_label_prefix} keyed by {data_type_desc}"
            chosen_method = "Timsort / Powersort (Python Built-in)"
            big_o = "O(n log n)"
            reason = "Floating-point values with uneven clustering or moderate counts are sorted fastest and most reliably by Python's C-level Timsort."
            sorted_result = [orig for _, orig in sorted(paired, key=lambda p: p[0], reverse=reverse)]

    elif all_strs:
        avg_len = sum(len(s) for s in keys) / n
        data_type_desc = f"variable-length strings (avg {avg_len:.1f} chars)"
        if data_label_prefix:
            data_type_desc = f"{data_label_prefix} keyed by {data_type_desc}"
        chosen_method = "Timsort / Powersort (Python Built-in)"
        big_o = "O(n log n)"
        reason = "Strings have varying lengths and can stop comparing at the first differing letter, making Timsort far more memory-efficient than Radix Sort."
        sorted_result = [orig for _, orig in sorted(paired, key=lambda p: p[0], reverse=reverse)]

    else:
        data_type_desc = "mixed / heterogeneous data types"
        chosen_method = "Type-Safe Timsort (Python Built-in)"
        big_o = "O(n log n)"
        reason = "The dataset mixes incompatible or non-finite types (such as numbers, strings, NaN, or None), so ranking by type before Timsort prevents a TypeError crash."
        sorted_result = [
            orig
            for _, orig in sorted(
                paired,
                key=_type_safe_sort_key,
                reverse=reverse,
            )
        ]

    actual_sec = time.perf_counter() - start_time
    if explain:
        min_sec, max_sec = _estimate_time_bounds_seconds(n, big_o, actual_sec)
        print(
            _format_classroom_report(
                n=n,
                data_type_desc=data_type_desc,
                discovered_key=discovered_key,
                chosen_method=chosen_method,
                big_o=big_o,
                min_sec=min_sec,
                max_sec=max_sec,
                actual_sec=actual_sec,
                reason=reason,
            )
        )

    return sorted_result
