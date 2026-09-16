# Delivery Trip Grouping Benchmark

## Running it

```bash
# Benchmark every registered algorithm on the sample data
python3 main.py --csv sample_deliveries.csv

# Same, but with a different capacity and more timing repetitions
python3 main.py --csv sample_deliveries.csv --capacity 8 --repeat 20

# Run just one algorithm, see its actual trip assignment, write it out
python3 main.py --csv sample_deliveries.csv --algorithm priority-queue --out trips.csv
```

## Benchmark metrics

For each algorithm, `benchmark.py` reports:

| Metric | Meaning |
|---|---|
| Time (ms) | best-of-N wall-clock time for `.group()` |
| Peak Mem (KB) | peak memory allocated during a run (`tracemalloc`) |
| Trips | number of trips produced (fewer is usually better) |
| Area Score | 0-1, how tightly same-area deliveries were kept together vs. the theoretical minimum trips that area's weight requires |
| Priority Score | 0-1, fraction of urgent/non-urgent delivery pairs correctly ordered across trips |
| Avg Util % | average % of vehicle capacity used per trip |

## Included algorithms

- **dummy-sequential** - packs deliveries in raw input order, no sorting.
  Baseline: shows what you get with zero cleverness.
- **priority-queue** - sorts strictly by priority (ties by input order)
  before packing. Maximizes priority score, ignores area entirely.

## Adding a new algorithm to benchmark

1. Create `algorithms/my_algorithm.py`:

   ```python
   from algorithms.base import GroupingAlgorithm

   class MyAlgorithm(GroupingAlgorithm):
       name = "my-algorithm"

       def group(self, deliveries, capacity):
           ordered = ...  # your custom ordering/grouping logic
           return self._first_fit_pack(ordered, capacity)  # or your own packer
   ```

2. Register it in `algorithms/__init__.py`:

   ```python
   from algorithms.my_algorithm import MyAlgorithm
   ALL_ALGORITHMS = [DummySequentialAlgorithm(), PriorityQueueAlgorithm(), MyAlgorithm()]
   ```

3. Run `python3 main.py --csv sample_deliveries.csv` - it now appears in
   the benchmark table automatically.
