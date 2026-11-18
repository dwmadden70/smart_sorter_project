# Lesson 3: Breaking the Profiler (Adversarial Dataset Design)

**Objective:** Read the decision rules in `src/smart_sorter.py` and engineer small `.json` datasets that deliberately push `smart_sort()` from one sorting algorithm to another.

---

## Background: How `smart_sort()` Makes Decisions

Before sorting, `smart_sort()` inspects your dataset and checks thresholds in this exact order:

1. **Trivial Size ($n \le 1$):** Returns immediately with **No Sort Needed**.
2. **Nearly Sorted ($n \ge 20$ and $\ge 85\%$ of adjacent pairs in order):** Picks **Timsort / Powersort**.
3. **Bounded Integers ($n \ge 500$ and $\text{max} - \text{min} \le 2n$):** Picks **Counting Sort**.
4. **Large Non-Negative Integers ($n \ge 50,000$ and $\text{min} \ge 0$):** Picks **Radix Sort**.
5. **Uniformly Distributed Floats ($n \ge 25,000$ across $\ge 7$ decile bins):** Picks **Bucket Sort**.
6. **Fallback:** Uses **Timsort / Powersort** (or **Type-Safe Timsort** if types are mixed or contain `NaN`/`Inf`).

---

## Challenge 1: Flip Counting Sort into Timsort with One Outlier

1. Write a short Python script to generate a JSON list of **600 random integers** between `0` and `100`, save it as `temp_counting.json`, and run:
   ```bash
   python main.py --file temp_counting.json
   ```
   *Confirm that `smart_sort()` selects **Counting Sort**.*

2. Now add **one single outlier**—the number `5000`—to the end of `temp_counting.json` and run `main.py --file temp_counting.json` again.
   * **What algorithm did `smart_sort()` pick now?**
   * **Why did adding just one number change the algorithm?** (Hint: Calculate $k = \text{max} - \text{min}$ and compare it to $2n$.)

---

## Challenge 2: Defeat the Nearly-Sorted Detector

1. Create a JSON file `temp_ordered.json` containing the integers `[1, 2, 3, ..., 100]`. Run `main.py --file temp_ordered.json` and confirm it reports `nearly sorted (100% already in order)`.
2. How many adjacent swaps does it take to drop `in_order_ratio` below `0.85` so `smart_sort()` stops treating the list as nearly sorted? Test your prediction!

---

## Challenge 3: Break Uniformity in Bucket Sort

In `_is_uniformly_distributed()` inside `src/smart_sorter.py`, a float dataset must populate **at least 7 out of 10 decile bins** and have **no single bin exceed $2.5\times$ the expected count**.

* Design a dataset of `30,000` floats between `0.0` and `100.0` where $90\%$ of the numbers cluster between `0.0` and `5.0`, and the remaining $10\%$ are spread between `5.0` and `100.0`.
* Run `main.py --file` on your skewed dataset. Which algorithm does `smart_sort()` choose instead of Bucket Sort, and why?
