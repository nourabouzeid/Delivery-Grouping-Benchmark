# Delivery Trip Grouping

## Running it

```bash
# Benchmark every registered algorithm on the sample data
python3 main.py --csv sample_deliveries.csv

# Same, but with a different capacity and more timing repetitions
python3 main.py --csv sample_deliveries.csv --capacity 8 --repeat 20

# Run just one algorithm, see its actual trip assignment, write it out
python3 main.py --csv sample_deliveries.csv --algorithm priority-queue --out trips.csv

# Generate delivery data
python3 generate_deliveries.py --count 50000 --seed 1 --out input/deliveries.csv
```
# Reasoning
## 1. Explain your solution approach in your own words.
The most important thing for me is making sure that trials are recorded, that I can start simple, see what's lacking (through recording metrics) and improve accordingly (this is why I chose to go with a benchmarking approach). So I started with the most naive methods (first-fit and priority-queue) then I moved on to a more reasonable approach which goes as follows:
1. **Group by area**.
2. **Sort by priority, then heaviest-first**.
3. **Best Fit** pack each area: put each delivery in the trip where it leaves the least wasted space.
4. **Merge the leftovers.** Each area's last trip is usually half empty, so I pull the underfilled
   trips (below 95% full) back out and re-pack them together across areas. This is what lets it keep
   utilization high.
5. **Dispatch the highest priority trips first.**.

This is the `cluster-priority-bfd-mix` algorithm (Results are discussed later).

## 2. What was the most difficult part of the assignment?
The ambiguity as to which metrics are more prioritized (priority vs area) which resulted in needing to do a benchmark and come up with metrics as well as research to make sure I can come up with an algorithm that can score well enough across the board.

## 3. Are there situations where your algorithm may not produce the best possible grouping? Explain.
Yes. Every algorithm here is a heuristic, so none guarantees the optimum. However they're extremely efficient and only sacrifice a little bit of accuracy for much more effiency compared to something that would get the absolute optimal grouping. A situation that would cause some issues with grouping would be few deliveries per area which would cause most trips to be partial.

## 4. If the input contained 1,000,000 delivery requests, what part of your solution might become slow or memory-intensive?

On the cluster-priority-bfd algorithm the time and space complexity are O(nlogn) and O(n) respectively
where n is the number of delieveries

So the time and memory used are still in a reasonable range and the exact numbers are recorded below

Loaded 1000000 valid delivery request(s) (vehicle capacity: 10.0 kg)

| Algorithm | Trips | Time (ms) | Peak Mem (KB) | Area Score | Priority Score | Avg Util % |
|---|--:|--:|--:|--:|--:|--:|
| cluster-priority-bfd | 507208 | 17429.0319 | 220935.50 | 0.996 | 0.997 | 99.6% |

## 5. What would you improve if you had another day to work on the solution?
- Run more benchmarks and plot graphs, showcasing how algorithms perform under different types of data distributions and vehicle capacity

- Research with more algorithms

- Add a distance metric such that different areas hold more meaning


# Additional feature: the benchmarking module

For each algorithm, `benchmark.py` reports:

| Metric | Meaning |
|---|---|
| Time (ms) | best-of-N wall-clock time for `.group()` |
| Peak Mem (KB) | peak memory allocated during a run (`tracemalloc`) |
| Trips | number of trips produced (fewer is usually better) |
| Area Score | 0-1, how tightly same-area deliveries were kept together vs. the theoretical minimum trips that area's weight requires |
| Priority Score | 0-1, fraction of urgent/non-urgent delivery pairs correctly ordered across trips |
| Avg Util % | average % of vehicle capacity used per trip |

## The 18 algorithms

| Group | Algorithms |
|---|---|
| Baselines | `first-fit` (input order), `priority-queue` (strict priority order) |
| Bin packing | `ffd`, `bfd` (weight-descending First/Best Fit), `bfd-area` (BFD with area-aware tie-breaking) |
| Cluster-first (by area) | `cluster-area`, `cluster-ffd`, `cluster-bfd`, plus `cluster-ffd-mix` and `cluster-bfd-mix`, which re-pack underfilled trips across areas |
| Cluster + priority | `cluster-priority-ffd`, `cluster-priority-bfd`, `cluster-priority-ffd-mix`, and `cluster-priority-bfd-mix` (**the last is the recommended default**) |
| Scoring / regret | `weighted-heuristic` (blends fit, area and urgency), `regret-insertion` (VRP-style regret-2) |
| Local search | `local-search`, `balanced-search` (Or-opt relocation + 2-swap refinement) |.

## Benchmark Results (10k rows)

| Algorithm | Trips | Time (ms) | Peak Mem (KB) | Area Score | Priority Score | Avg Util % |
|---|--:|--:|--:|--:|--:|--:|
| first-fit | 6673 | 4.1930 | 1540.65 | 0.514 | 0.503 | 75.3% |
| priority-queue | 6656 | 10.2892 | 1739.96 | 0.514 | 1.000 | 75.5% |
| ffd | 5052 | 29.8759 | 2348.44 | 0.516 | 0.500 | 99.4% |
| bfd | 5052 | 69.4595 | 2811.12 | 0.516 | 0.500 | 99.4% |
| bfd-area | 5052 | 23.3079 | 2411.04 | 0.860 | 0.803 | 99.4% |
| cluster-area | 5360 | 35.6146 | 3288.65 | 0.939 | 0.933 | 93.7% |
| cluster-ffd | 5126 | 37.0647 | 3054.27 | 0.982 | 0.933 | 98.0% |
| cluster-bfd | 5126 | 66.4428 | 3017.50 | 0.982 | 0.933 | 98.0% |
| cluster-ffd-mix | 5078 | 39.7208 | 2980.19 | 0.946 | 0.926 | 98.9% |
| cluster-bfd-mix | 5099 | 74.6420 | 3055.93 | 0.962 | 0.929 | 98.5% |
| cluster-priority-ffd | 5199 | 28.5730 | 2178.48 | 0.968 | 0.967 | 96.6% |
| cluster-priority-bfd | 5195 | 53.6866 | 2215.47 | 0.969 | 0.969 | 96.7% |
| cluster-priority-ffd-mix | 5159 | 30.1872 | 2181.80 | 0.940 | 0.967 | 97.4% |
| cluster-priority-bfd-mix | 5150 | 57.9711 | 2179.07 | 0.944 | 0.968 | 97.5% |
| weighted-heuristic | 5151 | 134.9718 | 2164.32 | 0.954 | 0.972 | 97.5% |
| regret-insertion | 5147 | 1761.6444 | 2157.91 | 0.964 | 0.964 | 97.6% |
| local-search | 5099 | 342.9597 | 3316.82 | 0.962 | 0.935 | 98.5% |
| balanced-search | 5169 | 449.0733 | 3428.91 | 0.962 | 0.971 | 97.2% |

## Adding a new algorithm to benchmark

1. Create `algorithms/my_algorithm.py`, or configure `ClusterFirstAlgorithm` if you are composing the existing steps:

   ```python
   from algorithms.base import GroupingAlgorithm
   from algorithms.cluster import ClusterFirstAlgorithm
   from algorithms.packing import first_fit, pack_ordered

   class MyAlgorithm(GroupingAlgorithm):
       name = "my-algorithm"

       def group(self, deliveries, capacity):
           return pack_ordered(deliveries, capacity, first_fit, decreasing=True)

   # Example composition — no new packer needed:
   # ClusterFirstAlgorithm("my-cluster", packer="best-fit", by_priority=True, merge_leftovers=True)
   ```

2. Register it in `algorithms/__init__.py`:

   ```python
   from algorithms.my_algorithm import MyAlgorithm
   ALL_ALGORITHMS = [..., MyAlgorithm()]
   ```

3. Run `python3 main.py --csv sample_deliveries.csv` — it now appears in
   the benchmark table automatically.
