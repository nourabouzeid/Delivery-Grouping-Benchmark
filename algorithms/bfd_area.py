"""
Area-affine Best Fit Decreasing.

Same sort as BFD (heaviest first) and the same tightest-fit rule, but when
several trips are equally tight (or within `slack` grid steps of tightest) it
prefers one already carrying the delivery's area. On a 0.1 kg weight grid the
tie set is huge, so this is free: identical trip count and utilization to BFD,
better area grouping. Trips are then dispatched most-urgent-first.

This is a reference point between plain BFD (area-blind) and the full
cluster-first pipelines: it shows how much area grouping you get from tie-
breaking alone, without clustering by area first.
"""

from typing import List

from algorithms.base import GroupingAlgorithm
from algorithms.packing import best_fit_area_affine, order_trips_by_urgency, sort_deliveries
from models import Delivery, Trip


class BFDAreaAlgorithm(GroupingAlgorithm):
    name = "bfd-area"

    def __init__(self, *, slack: float = 12.0):
        self.slack = slack

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        ordered = sort_deliveries(deliveries, decreasing=True)
        trips = best_fit_area_affine(ordered, capacity, slack=self.slack)
        return order_trips_by_urgency(trips)
