import csv
from pathlib import Path
from typing import List, Tuple

from models import Delivery, RejectedDelivery

# Expected header names (case-insensitive, whitespace-tolerant match)
_COLUMN_ALIASES = {
    "id": {"id"},
    "area": {"area"},
    "priority": {"priority"},
    "weight": {"package weight (kg)", "weight", "package weight"},
}


def _normalize_header(fieldnames: List[str]) -> dict:
    """Map our canonical field names -> actual column name in the CSV."""
    lookup = {}
    for fname in fieldnames:
        key = fname.strip().lower()
        for canonical, aliases in _COLUMN_ALIASES.items():
            if key in aliases:
                lookup[canonical] = fname
    missing = set(_COLUMN_ALIASES) - set(lookup)
    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {sorted(missing)}. "
            f"Found columns: {fieldnames}"
        )
    return lookup


def load_deliveries(
    csv_path: str,
    vehicle_capacity: float,
) -> Tuple[List[Delivery], List[RejectedDelivery]]:
    
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No such CSV file: {csv_path}")

    valid: List[Delivery] = []
    rejected: List[RejectedDelivery] = []

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return valid, rejected

        columns = _normalize_header(reader.fieldnames)

        for row in reader:
            
            raw = dict(row)
            delivery_id = str(row.get(columns["id"], "")).strip()
            area = str(row.get(columns["area"], "")).strip()
            priority_raw = str(row.get(columns["priority"], "")).strip()
            weight_raw = str(row.get(columns["weight"], "")).strip()

            if not delivery_id:
                rejected.append(RejectedDelivery(raw, "missing ID"))
                continue
            if not area:
                rejected.append(RejectedDelivery(raw, f"missing area (ID {delivery_id})"))
                continue

            try:
                priority = int(priority_raw)
            except ValueError:
                rejected.append(
                    RejectedDelivery(raw, f"invalid priority '{priority_raw}' (ID {delivery_id})")
                )
                continue

            try:
                weight = float(weight_raw)
            except ValueError:
                rejected.append(
                    RejectedDelivery(raw, f"invalid weight '{weight_raw}' (ID {delivery_id})")
                )
                continue

            if weight <= 0:
                rejected.append(
                    RejectedDelivery(raw, f"non-positive weight {weight}kg (ID {delivery_id})")
                )
                continue

            if weight > vehicle_capacity:
                rejected.append(
                    RejectedDelivery(
                        raw,
                        f"package weight {weight}kg exceeds vehicle capacity "
                        f"{vehicle_capacity}kg (ID {delivery_id}) - cannot ever be shipped",
                    )
                )
                continue

            valid.append(Delivery(id=delivery_id, area=area, priority=priority, weight=weight))

    return valid, rejected


def write_trips_csv(trips, out_path: str) -> None:
    """Write the final trip assignment out as a flat CSV for inspection."""
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Trip", "ID", "Area", "Priority", "Package Weight (kg)"])
        for trip in trips:
            for d in trip.deliveries:
                writer.writerow([trip.index, d.id, d.area, d.priority, d.weight])


def write_rejected_csv(rejected: List[RejectedDelivery], out_path: str) -> None:
    columns: List[str] = []
    for r in rejected:
        for key in r.raw:
            if key is not None and key not in columns:
                columns.append(key)

    reason_col = "Reason"
    while reason_col in columns:  # don't collide with an input column of the same name
        reason_col = "_" + reason_col

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns + [reason_col])
        for r in rejected:
            row = ["" if r.raw.get(c) is None else r.raw[c] for c in columns]
            writer.writerow(row + [r.reason])
