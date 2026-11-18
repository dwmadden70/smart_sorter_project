# Lesson 4: Automatic Schema Discovery Lab

**Objective:** Explore how `smart_sort()` inspects unfamiliar JSON and CSV files without hardcoded column names using statistical scoring in `_score_candidate_field()`.

---

## How Automatic Key Discovery Works

When you pass a list of dictionaries or CSV rows into `smart_sort(data)` without specifying `sort_key`, it flattens nested objects up to 3 levels deep and scores every field from `0.0` to `1.0` using four signals:

$$\text{Score} = (0.35 \times \text{Completeness}) + (0.35 \times \text{Type Fitness}) + (0.30 \times \text{Cardinality Ratio}) - \text{Depth Penalty} + \text{Hint Bonus}$$

* **Completeness:** Fraction of rows where the field is not `None` or `""` (fields below $50\%$ completeness are disqualified).
* **Type Fitness:** Numbers score `1.00`, ISO dates score `0.95`, short strings ($\le 24$ chars) score `0.80`, URLs score `0.25`, and booleans score `0.20`.
* **Cardinality Ratio:** Unique values divided by total non-null values. A column where every row has the exact same value scores `0.0` and is ignored.
* **Depth Penalty & Hint Bonus:** Top-level fields beat deeply nested fields (`-0.05` per dot level), while field names ending in `id`, `_at`, `date`, `time`, `code`, `num`, or `seq` receive a `+0.08` bonus.

---

## Hands-On Activity

### Step 1: Test Auto-Discovery on Existing Files
Run `main.py` on these two files without passing `--key`:

```bash
python main.py --file tests/data/products_schema_org.json
python main.py --file tests/data/weather_telemetry.csv
```

1. Which field did `smart_sort()` automatically choose for `products_schema_org.json`?
2. Which field did it choose for `weather_telemetry.csv`?

### Step 2: Design a Custom Multi-Column JSON Dataset
Create a new file `my_playlist.json` with at least 6 songs and these fields:
* `is_explicit` (boolean: `true` or `false`)
* `genre` (repeated string, e.g., `"Pop"` or `"Rock"`)
* `cover_url` (string starting with `"https://"`)
* `duration_sec` (integer seconds, e.g., `185`, `214`, `198`)
* `lyrics_summary` (a long sentence over 70 characters)

1. Before running `main.py`, predict which field will win the highest score in `_score_candidate_field()` and explain why each of the other four fields loses points.
2. Run `python main.py --file my_playlist.json` to verify your prediction!
3. Now override the auto-detected field using `--key genre` and observe how the output changes.
