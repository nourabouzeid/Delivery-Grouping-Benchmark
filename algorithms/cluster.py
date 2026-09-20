"""
Cluster-first grouping: pack each area independently, then optionally
merge underfilled leftover trips across areas (cluster-first, route-second).

Each named algorithm is a configured ClusterFirstAlgorithm so new
combinations (different packer, priority, leftover pass) stay one-liners.
"""

from typing import List

from algorithms.base import GroupingAlgorithm
from algorithms.packing import (
    PackFn,
    best_fit,
    first_fit,
    group_by_area,
    is_full_trip,
    order_trips_by_urgency,
    pack_ordered,
    redistribute_priorities,
    reindex_trips,
)
from models import Delivery, Trip

# A leftover pass only re-packs trips below this utilization. At 1.0 every
# area's last (partial) trip gets torn up and mixed, which cost ~0.1-0.25 of
# area score for <0.5% utilization. 0.95 keeps area >= ~0.94.
DEFAULT_MIN_KEEP_UTILIZATION = 0.95

_PACKERS = {
    "first-fit": first_fit,
    "best-fit": best_fit,
}


class ClusterFirstAlgorithm(GroupingAlgorithm):
    """
    Pipeline:
      1. Group deliveries by area (categorical clustering)
      2. Optionally sort each group (priority, then decreasing weight)
      3. Bin-pack each group with First Fit or Best Fit
      4. Optionally pull underfilled trips back out and re-pack them
         together as mixed leftover trips using the same sort + packer
      5. Optionally dispatch trips most-urgent-first (order_by_urgency).
         Trip order is a free lever for the priority metric: it moves no
         delivery, so trip count, utilization and area score are unchanged.
      6. Optionally redistribute priorities (redistribute): swap equal-weight
         deliveries between trips of the same area set so urgent ones sit in
         early trips. Also free for trip count / utilization / area score,
         and lets the weight-tight packers (which ignore priority while
         packing, so they pack tighter) recover priority afterwards.
    """

    def __init__(
        self,
        name: str,
        *,
        packer: str = "first-fit",
        decreasing: bool = False,
        by_priority: bool = False,
        merge_leftovers: bool = False,
        min_keep_utilization: float = DEFAULT_MIN_KEEP_UTILIZATION,
        order_by_urgency: bool = False,
        redistribute: bool = False,
    ):
        if packer not in _PACKERS:
            raise ValueError(f"Unknown packer {packer!r}; expected one of {sorted(_PACKERS)}")
        self.name = name
        self.packer: PackFn = _PACKERS[packer]
        self.decreasing = decreasing
        self.by_priority = by_priority
        self.merge_leftovers = merge_leftovers
        self.min_keep_utilization = min_keep_utilization
        self.order_by_urgency = order_by_urgency
        self.redistribute = redistribute

    def _pack(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        return pack_ordered(
            deliveries,
            capacity,
            self.packer,
            by_priority=self.by_priority,
            decreasing=self.decreasing,
        )

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        kept: List[Trip] = []
        leftovers: List[Delivery] = []

        for _, items in group_by_area(deliveries):
            packed = self._pack(items, capacity)
            if not self.merge_leftovers:
                kept.extend(packed)
                continue
            for trip in packed:
                if is_full_trip(trip, capacity, self.min_keep_utilization):
                    kept.append(trip)
                else:
                    leftovers.extend(trip.deliveries)

        if leftovers:
            kept.extend(self._pack(leftovers, capacity))

        if self.redistribute:
            return redistribute_priorities(kept)
        if self.order_by_urgency:
            return order_trips_by_urgency(kept)
        return reindex_trips(kept)


class ClusterAreaAlgorithm(ClusterFirstAlgorithm):
    """Group by area, then First Fit in original order within each area."""

    def __init__(self):
        super().__init__("cluster-area", redistribute=True)


class ClusterFFDAlgorithm(ClusterFirstAlgorithm):
    """Group by area, then First Fit Decreasing within each area."""

    def __init__(self):
        super().__init__("cluster-ffd", packer="first-fit", decreasing=True, redistribute=True)


class ClusterBFDAlgorithm(ClusterFirstAlgorithm):
    """Group by area, then Best Fit Decreasing within each area."""

    def __init__(self):
        super().__init__("cluster-bfd", packer="best-fit", decreasing=True, redistribute=True)


class ClusterFFDMixAlgorithm(ClusterFirstAlgorithm):
    """Area FFD, then re-pack underfilled fragments into mixed trips."""

    def __init__(self):
        super().__init__(
            "cluster-ffd-mix",
            packer="first-fit",
            decreasing=True,
            merge_leftovers=True,
            redistribute=True,
        )


class ClusterBFDMixAlgorithm(ClusterFirstAlgorithm):
    """Area BFD, then re-pack underfilled fragments into mixed trips."""

    def __init__(self):
        super().__init__(
            "cluster-bfd-mix",
            packer="best-fit",
            decreasing=True,
            merge_leftovers=True,
            redistribute=True,
        )


class ClusterPriorityFFDAlgorithm(ClusterFirstAlgorithm):
    """Area clusters, urgency-first (then heavy-first), packed with First Fit."""

    def __init__(self):
        super().__init__(
            "cluster-priority-ffd",
            packer="first-fit",
            decreasing=True,
            by_priority=True,
            order_by_urgency=True,
        )


class ClusterPriorityBFDAlgorithm(ClusterFirstAlgorithm):
    """Area clusters, urgency-first (then heavy-first), packed with Best Fit."""

    def __init__(self):
        super().__init__(
            "cluster-priority-bfd",
            packer="best-fit",
            decreasing=True,
            by_priority=True,
            order_by_urgency=True,
        )


class ClusterPriorityFFDMixAlgorithm(ClusterFirstAlgorithm):
    """Full combo: area → priority → FFD, leftover fragments mixed across areas."""

    def __init__(self):
        super().__init__(
            "cluster-priority-ffd-mix",
            packer="first-fit",
            decreasing=True,
            by_priority=True,
            merge_leftovers=True,
            order_by_urgency=True,
        )


class ClusterPriorityBFDMixAlgorithm(ClusterFirstAlgorithm):
    """Full combo: area → priority → BFD, leftover fragments mixed across areas."""

    def __init__(self):
        super().__init__(
            "cluster-priority-bfd-mix",
            packer="best-fit",
            decreasing=True,
            by_priority=True,
            merge_leftovers=True,
            order_by_urgency=True,
        )