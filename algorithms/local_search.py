"""
Or-opt + 2-swap local search.

Note on measured impact: on the 10k benchmark the two moves below find almost
nothing to improve once the start is a weight-tight, area-aware packing (at
most 1 trip in ~5100; 92% of trips already have <=0.3 kg slack and no
8-trip window can be repacked into fewer bins). The scores come from the
construction and the final priority redistribution; the search is a safety
net that matters more on messier inputs than on this uniform data.

Every algorithm elsewhere in this package is a single greedy pass: it
never revisits a decision once a delivery has landed in a trip. This one
does - it starts from a strong constructive baseline (Best Fit Decreasing)
and then repeatedly applies two classic local-search moves borrowed from
bin-packing / VRP literature:

  * Or-opt (relocate): try to empty out the lightest trips entirely by
    moving each of their deliveries into a different trip that still has
    room. A trip that empties out is dropped - something first-fit/best-fit
    can never do once a delivery has been placed, so this is the move that
    actually reduces trip count below the constructive baseline.

  * 2-swap (exchange): for nearby pairs of trips, try exchanging one
    delivery from each. A swap is only kept if both trips stay within
    capacity and it improves a local proxy for area clustering and
    priority ordering (an urgent delivery sitting in a later trip than a
    less-urgent one is a sign the swap should happen).

Both moves are bounded (a capped number of relocation candidates, a
sliding window of trip pairs for swaps) so this stays fast on large
inputs instead of doing an exhaustive neighbourhood search.
"""

from typing import Dict, List, Optional

from algorithms.base import GroupingAlgorithm
from algorithms.cluster import ClusterFirstAlgorithm
from algorithms.packing import redistribute_priorities, reindex_trips
from models import Delivery, Trip

_EPS = 1e-9


class LocalSearchAlgorithm(GroupingAlgorithm):
    name = "local-search"

    def __init__(
        self,
        *,
        name: str = "local-search",
        or_opt_passes: int = 3,
        or_opt_candidates_per_pass: int = 50,
        swap_window: int = 20,
        swap_w_area: float = 1.0,
        swap_w_priority: float = 0.5,
    ):
        self.name = name
        self.or_opt_passes = or_opt_passes
        self.or_opt_candidates_per_pass = or_opt_candidates_per_pass
        self.swap_window = swap_window
        # 2-swap's priority term assumes trip.index roughly tracks urgency,
        # which only holds for constructions that sort globally by
        # priority before packing (e.g. plain BFD). Subclasses that start
        # from an area-clustered baseline, where trip.index instead tracks
        # which area was processed first, should set swap_w_priority=0 -
        # otherwise the swap "fixes" that don't reflect real misordering.
        self.swap_w_area = swap_w_area
        self.swap_w_priority = swap_w_priority
        self._builder = ClusterFirstAlgorithm(
            f"{name}-init",
            packer="best-fit",
            decreasing=True,
            merge_leftovers=True,
        )

    # ---- construction ---------------------------------------------------

    def _initial_solution(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        # Area clusters, weight-descending Best Fit, underfilled fragments
        # merged across areas. Starting from plain BFD (area-blind) left
        # 2-swap unable to recover area grouping: measured area score 0.65.
        return self._builder.group(deliveries, capacity)

    # ---- Or-opt: try to eliminate the lightest trips ---------------------

    def _try_empty_trip(self, trip: Trip, others: List[Trip], capacity: float) -> bool:
        """
        Try to relocate every delivery in `trip` into `others`. All-or-nothing.

        Among feasible targets, a trip that already carries the delivery's
        area wins over tightest-fit alone - relocating to eliminate a trip
        shouldn't come at the cost of scattering areas that were already
        grouped together.
        """
        remaining: Dict[int, float] = {id(t): t.remaining_capacity(capacity) for t in others}
        areas: Dict[int, set] = {id(t): set(t.areas) for t in others}
        plan = []
        for delivery in trip.deliveries:
            target = None
            best_key = None
            for t in others:
                room = remaining[id(t)]
                if delivery.weight <= room + _EPS:
                    leftover = room - delivery.weight
                    area_match = 0 if delivery.area in areas[id(t)] else 1
                    key = (area_match, leftover)
                    if best_key is None or key < best_key:
                        best_key = key
                        target = t
            if target is None:
                return False
            plan.append((delivery, target))
            remaining[id(target)] -= delivery.weight
            areas[id(target)].add(delivery.area)

        for delivery, target in plan:
            target.add(delivery)
        return True

    def _or_opt(self, trips: List[Trip], capacity: float) -> List[Trip]:
        # Candidate selection below needs trips sorted by weight, but that
        # order has no relation to priority/area structure the constructor
        # built in - only *which* trips survive should carry through, not
        # the order they end up in. Restore original order before
        # returning so a downstream reindex doesn't scramble it.
        original_order = {id(t): t.index for t in trips}
        trips = list(trips)
        for _ in range(self.or_opt_passes):
            if len(trips) < 2:
                break
            trips.sort(key=lambda t: t.total_weight)
            candidates = trips[: min(self.or_opt_candidates_per_pass, len(trips))]

            emptied = []
            for trip in candidates:
                others = [t for t in trips if t is not trip and t not in emptied]
                if not others or not trip.deliveries:
                    continue
                if self._try_empty_trip(trip, others, capacity):
                    emptied.append(trip)

            if not emptied:
                break
            trips = [t for t in trips if t not in emptied]

        trips.sort(key=lambda t: original_order[id(t)])
        return trips

    # ---- 2-swap: exchange deliveries between nearby trips -----------------

    def _area_fit(self, trip: Trip, exclude: Delivery, incoming: Delivery) -> float:
        peers = [d for d in trip.deliveries if d is not exclude]
        if not peers:
            return 0.0
        return sum(1 for d in peers if d.area == incoming.area) / len(peers)

    def _swap_gain(self, trip_a: Trip, trip_b: Trip, da: Delivery, db: Delivery) -> float:
        before = self._area_fit(trip_a, da, da) + self._area_fit(trip_b, db, db)
        after = self._area_fit(trip_a, da, db) + self._area_fit(trip_b, db, da)
        area_gain = after - before

        priority_gain = 0.0
        if self.swap_w_priority and da.priority != db.priority:
            # An urgent delivery (lower number) belongs in the earlier trip.
            earlier, later = (trip_a, trip_b) if trip_a.index < trip_b.index else (trip_b, trip_a)
            earlier_item = da if earlier is trip_a else db
            later_item = db if earlier is trip_a else da
            priority_gain = 1.0 if earlier_item.priority > later_item.priority else -0.5

        return self.swap_w_area * area_gain + self.swap_w_priority * priority_gain

    def _try_swap(self, trip_a: Trip, trip_b: Trip, capacity: float) -> bool:
        best = None  # (gain, i, j)
        for i, da in enumerate(trip_a.deliveries):
            for j, db in enumerate(trip_b.deliveries):
                if da.area == db.area and da.priority == db.priority:
                    continue
                new_a = trip_a.total_weight - da.weight + db.weight
                new_b = trip_b.total_weight - db.weight + da.weight
                if new_a > capacity + _EPS or new_b > capacity + _EPS:
                    continue
                gain = self._swap_gain(trip_a, trip_b, da, db)
                if gain > _EPS and (best is None or gain > best[0]):
                    best = (gain, i, j)
        if best is None:
            return False
        _, i, j = best
        da, db = trip_a.deliveries[i], trip_b.deliveries[j]
        trip_a.deliveries[i], trip_b.deliveries[j] = db, da
        trip_a.total_weight += db.weight - da.weight
        trip_b.total_weight += da.weight - db.weight
        return True

    def _two_swap(self, trips: List[Trip], capacity: float) -> List[Trip]:
        n = len(trips)
        for a in range(n):
            window_end = min(a + 1 + self.swap_window, n)
            for b in range(a + 1, window_end):
                self._try_swap(trips[a], trips[b], capacity)
        return trips

    # ---- entry point ------------------------------------------------------

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        if not deliveries:
            return []

        trips = self._initial_solution(deliveries, capacity)
        trips = self._or_opt(trips, capacity)
        trips = self._two_swap(trips, capacity)
        # Free final step: re-deal equal-weight deliveries so urgent ones sit
        # in early trips, then dispatch most-urgent-first. Changes no trip's
        # weight or area set, so it cannot undo what the search achieved.
        return redistribute_priorities(trips)
