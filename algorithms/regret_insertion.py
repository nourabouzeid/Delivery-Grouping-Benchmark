"""
Regret-2 insertion.

A construction heuristic borrowed from VRP insertion methods. Rather than
committing to deliveries in a fixed order, it always places next whichever
delivery would be most "regretted" if delayed: the one whose best and
second-best trip both look nearly as good gets pushed later, while a
delivery with only one workable trip (or none at all) is placed
immediately, before some other delivery can take that slot away from it.

Insertion cost for a (delivery, trip) pair is the leftover capacity after
the fit (a best-fit-style term) plus a penalty if the trip already carries
a different area. Regret is the gap between a delivery's best and
second-best cost across open trips.

It runs inside each area cluster, then a final pass re-packs underfilled
fragments across areas (see pack_by_area_with_leftovers), so trips come out
area-coherent instead of fragmented across the whole city.

Two windows keep this bounded on large inputs: only a lookahead batch of
pending deliveries is scored on each iteration (instead of every remaining
delivery), and only the most-recently-opened trips are considered as
candidates (instead of every trip ever opened).
"""

from typing import List, Optional, Tuple

from algorithms.base import GroupingAlgorithm
from algorithms.packing import pack_by_area_with_leftovers
from models import Delivery, Trip

_EPS = 1e-9
_AREA_MISMATCH_PENALTY = 1.0  # kg-equivalent penalty for mixing areas in a trip


class RegretInsertionAlgorithm(GroupingAlgorithm):
    name = "regret-insertion"

    def __init__(
        self,
        *,
        name: str = "regret-insertion",
        batch_size: int = 25,
        candidate_window: int = 200,
        min_keep_utilization: float = 0.95,
    ):
        self.name = name
        self.batch_size = batch_size
        self.candidate_window = candidate_window
        self.min_keep_utilization = min_keep_utilization

    def _best_two(
        self,
        trips: List[Trip],
        trip_areas: List[set],
        delivery: Delivery,
        capacity: float,
    ) -> Tuple[Optional[int], Optional[float], Optional[float]]:
        """
        Best and second-best insertion cost over the candidate window.

        Insertion cost = leftover capacity after the fit (best-fit-style term)
        + a penalty when the trip already carries a different area. The
        arithmetic is inlined and each trip's area set is cached in
        `trip_areas`: this is the hot loop (tens of millions of evaluations on
        10k deliveries), and rebuilding `trip.areas` per evaluation dominated
        the runtime.
        """
        n = len(trips)
        start = max(0, n - self.candidate_window) if self.candidate_window else 0
        weight = delivery.weight
        area = delivery.area
        limit = capacity + _EPS
        best_idx, best_cost, second_cost = None, None, None
        for i in range(start, n):
            trip = trips[i]
            total = trip.total_weight
            if total + weight > limit:
                continue
            cost = capacity - total - weight
            if trip.deliveries and area not in trip_areas[i]:
                cost += _AREA_MISMATCH_PENALTY
            if best_cost is None or cost < best_cost:
                second_cost = best_cost
                best_cost = cost
                best_idx = i
            elif second_cost is None or cost < second_cost:
                second_cost = cost
        return best_idx, best_cost, second_cost

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
        """Regret-2 insertion over one batch of deliveries."""
        # Urgent-first / heaviest-first ordering feeds the lookahead batch;
        # regret then decides the exact placement order within it.
        pending = sorted(deliveries, key=lambda d: (d.priority, -d.weight))
        trips: List[Trip] = []
        trip_areas: List[set] = []

        while pending:
            batch_end = min(self.batch_size, len(pending))
            best_local_idx = 0
            best_trip_idx: Optional[int] = None
            best_regret = -1.0

            for i in range(batch_end):
                t_idx, best_cost, second_cost = self._best_two(
                    trips, trip_areas, pending[i], capacity
                )
                if t_idx is None:
                    regret = float("inf")  # nothing fits: place it now, no choice to lose
                else:
                    regret = (second_cost - best_cost) if second_cost is not None else 0.0
                if regret > best_regret + _EPS:
                    best_regret = regret
                    best_local_idx = i
                    best_trip_idx = t_idx

            delivery = pending.pop(best_local_idx)
            if best_trip_idx is None:
                trip = self._new_trip(trips)
                trip_areas.append(set())
                best_trip_idx = len(trips) - 1
            else:
                trip = trips[best_trip_idx]
            trip.add(delivery)
            trip_areas[best_trip_idx].add(delivery.area)

        return trips
