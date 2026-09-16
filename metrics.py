import math
from collections import defaultdict
from itertools import combinations
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

    Computed as a pairwise ranking accuracy: for every pair of deliveries
    (a, b) with a strictly more urgent than b, check whether a's trip
    index is <= b's trip index. Score = fraction of such pairs that are
    correctly ordered. Pairs with equal priority are ignored (there's no
    "correct" order to enforce between them).

    score ~ [0, 1], where 1 is a perfect priority adherence
    """

    all_deliveries = [(d, trip.index) for trip in trips for d in trip.deliveries]
    if len(all_deliveries) < 2:
        return 1.0

    correct = 0
    total = 0
    for (d1, t1), (d2, t2) in combinations(all_deliveries, 2):
        if d1.priority == d2.priority:
            continue
        if d1.priority < d2.priority:
            urgent_trip, other_trip = t1, t2
        else:
            urgent_trip, other_trip = t2, t1
        total += 1
        if urgent_trip <= other_trip:
            correct += 1

    return 1.0 if total == 0 else correct / total


def num_trips(trips: List[Trip]) -> int:
    return len(trips)


def average_trip_utilization(trips: List[Trip], capacity: float) -> float:
    """Average fraction of vehicle capacity used per trip (0.0 - 1.0)."""
    if not trips:
        return 0.0
    return sum(t.total_weight / capacity for t in trips) / len(trips)
