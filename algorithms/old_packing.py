"""
Shared bin-packing primitives.

True First Fit / Best Fit scan every open trip (unlike the next-fit helper
on GroupingAlgorithm, which only tries the current trip). New algorithms
should use these so FFD/BFD and cluster pipelines compose cleanly.
"""

from collections import OrderedDict
from typing import Callable, Iterable, List, Sequence, Tuple

from models import Delivery, Trip

PackFn = Callable[[Sequence[Delivery], float], List[Trip]]


def reindex_trips(trips: Iterable[Trip]) -> List[Trip]:
    """Return a new list of trips numbered 0..n-1, preserving contents."""
    reindexed: List[Trip] = []
    for i, trip in enumerate(trips):
        reindexed.append(Trip(index=i, deliveries=list(trip.deliveries)))
    return reindexed


def sort_deliveries(
    deliveries: Sequence[Delivery],
    *,
    by_priority: bool = False,
    decreasing: bool = False,
) -> List[Delivery]:
    """
    Stable sort. Priority ascending (more urgent first) is the primary key
    when requested; decreasing weight is the next key (classic FFD/BFD).
    """
    if not by_priority and not decreasing:
        return list(deliveries)

    def key(d: Delivery):
        parts = []
        if by_priority:
            parts.append(d.priority)
        if decreasing:
            parts.append(-d.weight)
        return tuple(parts)

    return sorted(deliveries, key=key)


def group_by_area(deliveries: Sequence[Delivery]) -> List[Tuple[str, List[Delivery]]]:
    """Partition deliveries by area, preserving first-seen area order and input order within each area."""
    groups: OrderedDict[str, List[Delivery]] = OrderedDict()
    for delivery in deliveries:
        groups.setdefault(delivery.area, []).append(delivery)
    return list(groups.items())


def first_fit(ordered_deliveries: Sequence[Delivery], capacity: float) -> List[Trip]:
    """Place each delivery in the earliest trip that can take it; else open a new trip."""
    trips: List[Trip] = []
    for delivery in ordered_deliveries:
        placed = False
        for trip in trips:
            if trip.can_fit(delivery, capacity):
                trip.add(delivery)
                placed = True
                break
        if not placed:
            trip = Trip(index=len(trips))
            trip.add(delivery)
            trips.append(trip)
    return trips


def best_fit(ordered_deliveries: Sequence[Delivery], capacity: float) -> List[Trip]:
    """
    Place each delivery in the feasible trip with the least leftover capacity
    after the placement. Open a new trip only when nothing fits.
    """
    trips: List[Trip] = []
    for delivery in ordered_deliveries:
        best: Trip = None
        best_slack = None
        for trip in trips:
            if not trip.can_fit(delivery, capacity):
                continue
            slack = trip.remaining_capacity(capacity) - delivery.weight
            if best is None or slack < best_slack:
                best = trip
                best_slack = slack
        if best is None:
            best = Trip(index=len(trips))
            trips.append(best)
        best.add(delivery)
    return trips


def pack_ordered(
    deliveries: Sequence[Delivery],
    capacity: float,
    packer: PackFn,
    *,
    by_priority: bool = False,
    decreasing: bool = False,
) -> List[Trip]:
    ordered = sort_deliveries(deliveries, by_priority=by_priority, decreasing=decreasing)
    return packer(ordered, capacity)


def is_full_trip(trip: Trip, capacity: float, min_keep_utilization: float) -> bool:
    if capacity <= 0:
        return True
    return (trip.total_weight / capacity) + 1e-9 >= min_keep_utilization
