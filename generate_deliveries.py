"""
Generate a large delivery-requests CSV for benchmarking.

Usage:
    python3 generate_deliveries.py
    python3 generate_deliveries.py --count 50000 --out input/deliveries.csv
    python3 generate_deliveries.py --count 10000 --seed 42 --max-weight 10
"""

import argparse
import csv
import random
from pathlib import Path

AREAS = [
    "Nasr City",
    "Maadi",
    "Zamalek",
    "Heliopolis",
    "Downtown",
    "Dokki",
    "Mohandessin",
    "Garden City",
    "New Cairo",
    "6th of October",
    "Giza",
    "Helwan",
    "Shubra",
    "Ain Shams",
    "Rehab",
    "Madinaty",
    "Sheikh Zayed",
    "5th Settlement",
    "Agouza",
    "Manial",
]

DEFAULT_COUNT = 10_000
DEFAULT_OUT = "input/generated_deliveries.csv"
DEFAULT_MAX_WEIGHT = 10.0
DEFAULT_MIN_WEIGHT = 0.1
DEFAULT_MIN_PRIORITY = 1
DEFAULT_MAX_PRIORITY = 5


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic delivery CSV data")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of deliveries to generate (default: {DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output CSV path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for reproducible data (default: none)",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=DEFAULT_MIN_WEIGHT,
        help=f"Minimum package weight in kg (default: {DEFAULT_MIN_WEIGHT})",
    )
    parser.add_argument(
        "--max-weight",
        type=float,
        default=DEFAULT_MAX_WEIGHT,
        help=f"Maximum package weight in kg (default: {DEFAULT_MAX_WEIGHT})",
    )
    parser.add_argument(
        "--min-priority",
        type=int,
        default=DEFAULT_MIN_PRIORITY,
        help=f"Lowest (most urgent) priority value (default: {DEFAULT_MIN_PRIORITY})",
    )
    parser.add_argument(
        "--max-priority",
        type=int,
        default=DEFAULT_MAX_PRIORITY,
        help=f"Highest (least urgent) priority value (default: {DEFAULT_MAX_PRIORITY})",
    )
    return parser.parse_args()


def generate_rows(count, min_weight, max_weight, min_priority, max_priority, rng):
    if count < 1:
        raise ValueError("--count must be at least 1")
    if min_weight <= 0:
        raise ValueError("--min-weight must be positive")
    if max_weight < min_weight:
        raise ValueError("--max-weight must be >= --min-weight")
    if max_priority < min_priority:
        raise ValueError("--max-priority must be >= --min-priority")

    rows = []
    for i in range(1, count + 1):
        weight = round(rng.uniform(min_weight, max_weight), 1)
        if weight <= 0:
            weight = min_weight
        rows.append(
            {
                "ID": i,
                "Area": rng.choice(AREAS),
                "Priority": rng.randint(min_priority, max_priority),
                "Package Weight (kg)": weight,
            }
        )
    return rows


def write_csv(path, rows):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["ID", "Area", "Priority", "Package Weight (kg)"]
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    rng = random.Random(args.seed)
    rows = generate_rows(
        args.count,
        args.min_weight,
        args.max_weight,
        args.min_priority,
        args.max_priority,
        rng,
    )
    write_csv(args.out, rows)
    print(f"Wrote {len(rows)} deliveries to {args.out}")


if __name__ == "__main__":
    main()
