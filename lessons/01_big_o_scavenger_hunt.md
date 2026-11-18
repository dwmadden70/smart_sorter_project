# Lesson 1: Big O Scavenger Hunt

**Objective:** Inspect real-world datasets using `main.py --file`, observe how `smart_sort()` profiles data shapes in a single $O(n)$ pass, and explain why different algorithms win on different datasets.

---

## Part 1: Run the Scavenger Hunt

From the project root directory, run `python main.py --file <path>` on each dataset listed below and fill in the table using the `[smart_sort Classroom Report]` printed in your terminal.

| Dataset File | Record Count ($n$) | Auto-Detected Field | Chosen Sort Method | Big O | Actual Time (sec) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/data/student_scores.json` | | | | | |
| `tests/data/shipment_tracking_ids.json` | | | | | |
| `tests/data/gps_elevation_readings.json` | | | | | |
| `tests/data/server_audit_log.csv` | | | | | |
| `tests/data/mixed_sensor_dump.json` | | | | | |
| `tests/data/author_quotes.txt` | | | | | |

---

## Part 2: Critical Thinking Questions

1. **Counting Sort vs. Radix Sort:**
   Both `student_scores.json` and `shipment_tracking_ids.json` contain integers. Why did `smart_sort()` choose **Counting Sort** for student scores, but **Radix Sort** for shipment tracking IDs? What would happen to memory usage if Counting Sort were used on 9-digit tracking IDs?

2. **The Power of Nearly Sorted Data:**
   Look at `server_audit_log.csv`. What percentage of adjacent records were already in order? Explain how Timsort takes advantage of existing runs to avoid $O(n \log n)$ work.

3. **Preventing Crashes on Messy Data:**
   What happened when you ran `mixed_sensor_dump.json`? Why would Python's standard `sorted()` raise a `TypeError` on that file without `Type-Safe Timsort`?

4. **Check Your Generated Reports:**
   Open the `tests/results/` folder and inspect one of the `custom_inspection_*.md` files created during your runs. What extra details are included when a non-built-in algorithm is chosen?
