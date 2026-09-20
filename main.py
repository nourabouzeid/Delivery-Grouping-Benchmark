"""
io_utils.load_deliveries()   -> validated Delivery objects
algorithms.ALL_ALGORITHMS    -> strategies to benchmark
benchmark.run_all()          -> timings + quality scores
io_utils.write_trips_csv()   -> optional output file

Usage:
    python main.py --csv sample_deliveries.csv
    python main.py --csv sample_deliveries.csv --capacity 10 --repeat 10
    python main.py --csv sample_deliveries.csv --algorithm priority-queue --out trips.csv
"""

import argparse
import sys
from pathlib import Path
from typing import List

from algorithms import ALL_ALGORITHMS
from benchmark import print_report, run_all, run_benchmark
from io_utils import load_deliveries, write_trips_csv
from models import Delivery, RejectedDelivery

DEFAULT_CAPACITY_KG = 10.0


def output_path_for_algorithm(out_path: str, algorithm_name: str) -> str:
    """Insert the algorithm name before the file extension, e.g. trips.csv -> trips_priority-queue.csv."""
    path = Path(out_path)
    suffix = path.suffix or ".csv"
    safe_name = algorithm_name.replace("/", "-")
    return str(path.with_name(f"{path.stem}_{safe_name}{suffix}"))


def parse_args():
    parser = argparse.ArgumentParser(description="Delivery trip grouping & benchmarking")
    parser.add_argument("--csv", required=True, help="Path to the delivery requests CSV")
    parser.add_argument("--capacity", type=float, default=DEFAULT_CAPACITY_KG,
                         help=f"Vehicle capacity in kg (default: {DEFAULT_CAPACITY_KG})")
    parser.add_argument("--repeat", type=int, default=5,
                         help="Number of timed repetitions per algorithm (default: 5)")
    parser.add_argument("--algorithm", choices=[a.name for a in ALL_ALGORITHMS],
                         help="Run only this one algorithm and print its trips in detail "
                              "(default: benchmark all registered algorithms)")
    parser.add_argument(
        "--out",
        help="Optional path to write trip assignments as CSV. When running all algorithms, "
             "one file is written per algorithm (the algorithm name is inserted into the filename).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    deliveries: List[Delivery]
    rejected: List[RejectedDelivery]
    
    try:
        deliveries, rejected  = load_deliveries(args.csv, args.capacity)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading '{args.csv}': {e}", file=sys.stderr)
        sys.exit(1)

    if rejected:
        print(f"Rejected {len(rejected)} row(s) from input:")
        for r in rejected:
            print(r)
        print()

    if not deliveries:
        print("No valid deliveries to process - nothing to schedule.")
        return

    print(f"Loaded {len(deliveries)} valid delivery request(s) "
          f"(vehicle capacity: {args.capacity} kg)\n")

    if args.algorithm:
        algo = next(a for a in ALL_ALGORITHMS if a.name == args.algorithm)
        result = run_benchmark(algo, deliveries, args.capacity, repeat=args.repeat)
        print_report([result])
        print(f"\nTrips produced by '{algo.name}':")
        for trip in result.trips:
            print(f"  {trip}")
        if args.out:
            write_trips_csv(result.trips, args.out)
            print(f"\nWrote trip assignment to {args.out}")
    else:
        results = run_all(ALL_ALGORITHMS, deliveries, args.capacity, repeat=args.repeat)
        print_report(results)
        if args.out:
            print()
            for result in results:
                out_path = output_path_for_algorithm(args.out, result.algorithm_name)
                write_trips_csv(result.trips, out_path)
                print(f"Wrote trip assignment ({result.algorithm_name}) to {out_path}")


if __name__ == "__main__":
    main()
