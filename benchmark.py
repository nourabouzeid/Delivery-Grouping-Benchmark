import time
import tracemalloc
from dataclasses import dataclass, field
from typing import List

from algorithms.base import GroupingAlgorithm
from metrics import (
    area_grouping_score,
    average_trip_utilization,
    num_trips,
    priority_adherence_score,
)
from models import Delivery, Trip


@dataclass
class BenchmarkResult:
    algorithm_name: str
    num_deliveries: int
    time_seconds: float          # best-of-`repeat` wall clock time
    peak_memory_bytes: int       # peak memory during a single timed run
    trip_count: int
    area_grouping_score: float
    priority_adherence_score: float
    avg_trip_utilization: float
    trips: List[Trip] = field(repr=False)


def _run_once(
    algorithm: GroupingAlgorithm,
    deliveries: List[Delivery],
    capacity: float,
    *,
    trace_memory: bool = False,
):
    input_copy = list(deliveries)

    if trace_memory:
        tracemalloc.start()
    start = time.perf_counter()
    trips = algorithm.group(input_copy, capacity)
    elapsed = time.perf_counter() - start
    peak = 0
    if trace_memory:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    return trips, elapsed, peak


def run_benchmark(
    algorithm: GroupingAlgorithm,
    deliveries: List[Delivery],
    capacity: float,
    repeat: int = 5,
) -> BenchmarkResult:
    """
    Run one algorithm `repeat` times and keep the best timing 
    plus the peak memory across those runs.
    """
    if not deliveries:
        return BenchmarkResult(
            algorithm_name=algorithm.name,
            num_deliveries=0,
            time_seconds=0.0,
            peak_memory_bytes=0,
            trip_count=0,
            area_grouping_score=1.0,
            priority_adherence_score=1.0,
            avg_trip_utilization=0.0,
            trips=[],
        )

    best_time = None
    peak_mem = 0
    trips = None
    n_repeat = max(1, repeat)
    for i in range(n_repeat):
        run_trips, elapsed, peak = _run_once(
            algorithm,
            deliveries,
            capacity,
            trace_memory=(i == 0),
        )
        peak_mem = max(peak_mem, peak)
        if best_time is None or elapsed < best_time:
            best_time = elapsed
            trips = run_trips

    return BenchmarkResult(
        algorithm_name=algorithm.name,
        num_deliveries=len(deliveries),
        time_seconds=best_time,
        peak_memory_bytes=peak_mem,
        trip_count=num_trips(trips),
        area_grouping_score=area_grouping_score(trips, capacity),
        priority_adherence_score=priority_adherence_score(trips),
        avg_trip_utilization=average_trip_utilization(trips, capacity),
        trips=trips,
    )


def run_all(
    algorithms: List[GroupingAlgorithm],
    deliveries: List[Delivery],
    capacity: float,
    repeat: int = 5,
) -> List[BenchmarkResult]:
    results = []
    total = len(algorithms)
    for i, algo in enumerate(algorithms, start=1):
        print(f"[{i}/{total}] Running {algo.name} ({repeat} timed run(s))...", flush=True)
        results.append(run_benchmark(algo, deliveries, capacity, repeat=repeat))
    return results


def print_report(results: List[BenchmarkResult]) -> None:
    if not results:
        print("No results to report.")
        return

    header = (
        f"{'Algorithm':<28}{'Trips':>7}{'Time (ms)':>12}{'Peak Mem (KB)':>16}"
        f"{'Area Score':>12}{'Priority Score':>16}{'Avg Util %':>12}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.algorithm_name:<28}{r.trip_count:>7}{r.time_seconds * 1000:>12.4f}"
            f"{r.peak_memory_bytes / 1024:>16.2f}{r.area_grouping_score:>12.3f}"
            f"{r.priority_adherence_score:>16.3f}{r.avg_trip_utilization * 100:>11.1f}%"
        )
