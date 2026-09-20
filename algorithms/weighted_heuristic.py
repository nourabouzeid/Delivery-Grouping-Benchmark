"""
Weighted Heuristic Scoring.

Every other packer here decides where a delivery goes using a single
signal (tightest fit, earliest slot, raw input order...). This algorithm
scores every open trip on a *weighted blend* of three signals at once and
drops the delivery into whichever trip scores highest:

  * fit      - how snugly the delivery would fill the trip's remaining
               capacity (a best-fit-style signal).
  * area     - how much of the trip's current load already shares this
               delivery's area (keeps areas clustered without a separate
               cluster-first pass).
  * urgency  - how much this delivery "wants" an early trip, scaled by how
               urgent it is (low priority number = more urgent = stronger
               preference for a low trip index).

The pass runs inside each area cluster and a final pass re-packs underfilled
fragments across areas (see pack_by_area_with_leftovers). Scoring alone can't
deliver area grouping: when deliveries are visited priority-major across the
whole city, no trip ever gets to specialise in one area no matter how the
weights are set (measured: area plateaus ~0.72 for any weight mix).

Deliveries are still visited urgent-first / heaviest-first so the scorer
always has the widest choice of trips for the requests that matter most,
but the *placement* decision - not just the visiting order - is what's
weighted here, which is what distinguishes it from priority-queue or the
cluster-priority pipelines.
"""

from typing import List, Optional

from algorithms.base import GroupingAlgorithm
from algorithms.packing import pack_by_area_with_leftovers
from models import Delivery, Trip

_EPS = 1e-9


class WeightedHeuristicAlgorithm(GroupingAlgorithm):
    name = "weighted-heuristic"

    def __init__(
        self,
        *,
        name: str = "weighted-heuristic",
        w_fit: float = 0.5,
        w_area: float = 0.3,
        w_priority: float = 0.2,
        candidate_window: int = 200,
        min_keep_utilization: float = 0.95,
    ):
        self.name = name
        self.w_fit = w_fit
        self.w_area = w_area
        self.w_priority = w_priority
        # Only score the most-recently-opened trips: they're the ones most
        # likely to still have room, and it keeps scoring O(n) instead of
        # O(n * total_trips) on large inputs.
        self.candidate_window = candidate_window
        self.min_keep_utilization = min_keep_utilization

    def _score(self, trip: Trip, delivery: Delivery, capacity: float, max_priority: int, num_trips_open: int) -> float:
        remaining = trip.remaining_capacity(capacity)
        fit_score = min(1.0, delivery.weight / remaining) if remaining > _EPS else 0.0

        if trip.deliveries:
            area_score = sum(1 for d in trip.deliveries if d.area == delivery.area) / len(trip.deliveries)
        else:
            area_score = 0.0

        urgency = 1.0 - (delivery.priority / (max_priority + 1))
        earliness = 1.0 - (trip.index / num_trips_open) if num_trips_open else 1.0
        priority_score = urgency * earliness

        return self.w_fit * fit_score + self.w_area * area_score + self.w_priority * priority_score

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        if not deliveries:
            return []
        return pack_by_area_with_leftovers(
            deliveries,
            capacity,
            self._construct,
            min_keep_utilization=self.min_keep_utilization,
        )

    def _construct(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        """The weighted-scoring placement pass over one batch of deliveries."""
        max_priority = max(d.priority for d in deliveries)
        ordered = sorted(deliveries, key=lambda d: (d.priority, -d.weight))

        trips: List[Trip] = []
        for delivery in ordered:
            candidates = trips[-self.candidate_window:] if self.candidate_window else trips
            best_trip: Optional[Trip] = None
            best_score = -1.0
            for trip in candidates:
                if not trip.can_fit(delivery, capacity):
                    continue
                score = self._score(trip, delivery, capacity, max_priority, len(trips))
                if score > best_score + _EPS:
                    best_score = score
                    best_trip = trip
            if best_trip is None:
                best_trip = self._new_trip(trips)
            best_trip.add(delivery)

        return trips
