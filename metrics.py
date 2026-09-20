import math
from collections import defaultdict
from typing import List

from models import Trip


def area_grouping_score(trips: List[Trip], capacity: float) -> float:
    """
    How well are same-area deliveries kept together?

    For each area, compute the ideal_trip_count: minimum number of trips its total weight
    could theoretically fit into (ceil(total_weight / capacity)).

    score = ideal_trip_count / actual_trip_count, averaged across areas
    (weighted by number of deliveries in that area). 

    score ~ [0, 1], where 1 is a perfect area grouping
    """
    if not trips:
        return 1.0 

    area_weight = defaultdict(float)
    area_trip_sets = defaultdict(set)
    area_delivery_count = defaultdict(int)

    for trip in trips:
        for d in trip.deliveries:
            area_weight[d.area] += d.weight
            area_trip_sets[d.area].add(trip.index)
            area_delivery_count[d.area] += 1

    total_deliveries = sum(area_delivery_count.values())
    if total_deliveries == 0:
        return 1.0

    weighted_score = 0.0
    for area, weight in area_weight.items():
        ideal = max(1, math.ceil(weight / capacity - 1e-9))
        actual = len(area_trip_sets[area])
        area_score = min(1.0, ideal / actual)
        weighted_score += area_score * (area_delivery_count[area] / total_deliveries)

    return weighted_score


def priority_adherence_score(trips: List[Trip]) -> float:
    """
    Did more urgent deliveries end up in earlier trips compared to less urgent ones?

    Pairwise ranking accuracy: for every pair of deliveries (a, b) with a
    strictly more urgent than b, check whether a's trip index is <= b's trip
    index. Score = fraction of such pairs that are correctly ordered. Pairs
    with equal priority are ignored.

    Computed in O(n + P * T) via trip-index histograms (same result as
    enumerating all pairs).

    score ~ [0, 1], where 1 is a perfect priority adherence
    """
    if sum(len(trip.deliveries) for trip in trips) < 2:
        return 1.0

    by_priority = defaultdict(list)
    max_trip = 0
    for trip in trips:
        max_trip = max(max_trip, trip.index)
        for d in trip.deliveries:
            by_priority[d.priority].append(trip.index)

    if len(by_priority) < 2:
        return 1.0

    hist = [0] * (max_trip + 1)
    less_count = 0
    correct = 0
    total = 0

    # Least-urgent class first, so the histogram is always "everyone less urgent".
    for priority in sorted(by_priority, reverse=True):
        current = by_priority[priority]
        if less_count:
            suffix = [0] * (max_trip + 2)
            running = 0
            for t in range(max_trip, -1, -1):
                running += hist[t]
                suffix[t] = running
            for t in current:
                total += less_count
                correct += suffix[t]
        for t in current:
            hist[t] += 1
            less_count += 1

    return 1.0 if total == 0 else correct / total


def num_trips(trips: List[Trip]) -> int:
    return len(trips)


def average_trip_utilization(trips: List[Trip], capacity: float) -> float:
    """Average fraction of vehicle capacity used per trip (0.0 - 1.0)."""
    if not trips:
        return 0.0
    return sum(t.total_weight / capacity for t in trips) / len(trips)
