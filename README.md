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

Baselines:

- **first-fit** — packs deliveries in raw input order (next-fit: try the current trip, else open a new one).
- **priority-queue** — sorts strictly by priority (ties by input order) before packing.

Bin packing:

- **ffd** — First Fit Decreasing: sort by weight descending, place each item in the earliest trip that fits.
- **bfd** — Best Fit Decreasing: sort by weight descending, place each item in the feasible trip with the least leftover space.

Cluster-first (by area):

- **cluster-area** — group by area, then First Fit in original order within each area.
- **cluster-ffd** / **cluster-bfd** — group by area, then FFD or BFD inside each area.
- **cluster-ffd-mix** / **cluster-bfd-mix** — same, then a second pass that merges underfilled leftover trips across areas into mixed trips (cluster-first, route-second).
- **cluster-priority-ffd** / **cluster-priority-bfd** — within each area, sort by priority ascending then weight descending, then First Fit / Best Fit.
- **cluster-priority-ffd-mix** / **cluster-priority-bfd-mix** — full pipeline: area clusters → urgency-first sort → FFD/BFD → leftover mix pass.

A leftover (mixed) pass only re-packs trips whose utilization is below a full load (`min_keep_utilization`, default 1.0). Dedicated full trips stay area-pure.

Weighted / regret-based construction:

- **weighted-heuristic** — visits deliveries urgent-first / heaviest-first, but instead of a single placement rule, scores every open trip on a weighted blend of fit tightness, area affinity, and urgency-vs-trip-recency, and drops the delivery into the highest-scoring feasible trip.
- **regret-insertion** — a VRP-style regret-2 insertion heuristic: for a lookahead batch of pending deliveries, computes each one's best and second-best trip (by leftover capacity + an area-mismatch penalty), and places whichever delivery would lose the most by being delayed first.

Local search (improves an existing solution):

- **local-search** — builds an initial Best Fit Decreasing solution, then repeatedly applies Or-opt (try to empty out the lightest trips by relocating all their deliveries elsewhere, dropping any trip that fully empties) and 2-swap (exchange one delivery between two nearby trips when it improves area clustering or fixes a priority-ordering violation).
- **balanced-search** — same Or-opt / 2-swap refinement, but starts from the cluster-priority-bfd-mix baseline instead of plain BFD, and disables 2-swap's priority-fixing term (that heuristic assumes trip order tracks urgency, which only holds for globally-priority-sorted constructions). Aimed at scoring reasonably on *every* metric at once rather than maxing out one or two: on the 10k-row benchmark it lands near the top on trip count, area score, and utilization simultaneously, at some cost to priority score versus the pure cluster-priority pipelines.

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
