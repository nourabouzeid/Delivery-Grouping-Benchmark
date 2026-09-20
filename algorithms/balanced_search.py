"""
Balanced search.

Every algorithm above optimizes hard for one or two metrics at the expense
of the others: BFD/FFD chase trip count and utilization but ignore area
and priority; the cluster-priority pipelines protect area and priority but
leave trip count and utilization on the table; local-search polishes a
tight-packing baseline that never had area/priority structure to begin
with.

This one is built to be decent everywhere at once, by combining the two
techniques that already work well on *different* metrics:

  1. Construction: reuse the cluster-priority-bfd-mix pipeline (area
     clusters -> urgency-first sort -> Best Fit -> leftover-fragment
     merge). This is the strongest existing baseline for area grouping and
     priority adherence, and it's already close to full utilization.
  2. Refinement: run the Or-opt / 2-swap local search from
     `local_search.py` on top of that, which chases the trip count and
     utilization down further - the two metrics the constructive baseline
     alone doesn't push hard on.

Because Or-opt's relocation step is area-aware (see local_search.py), the
refinement pass mostly trades away *slack*, not the area/priority
structure the construction step already built in.
"""

from typing import List

from algorithms.cluster import ClusterFirstAlgorithm
from algorithms.local_search import LocalSearchAlgorithm
from models import Delivery, Trip


class BalancedSearchAlgorithm(LocalSearchAlgorithm):
    name = "balanced-search"

    def __init__(
        self,
        *,
        name: str = "balanced-search",
        or_opt_passes: int = 4,
        or_opt_candidates_per_pass: int = 80,
        swap_window: int = 30,
    ):
        super().__init__(
            name=name,
            or_opt_passes=or_opt_passes,
            or_opt_candidates_per_pass=or_opt_candidates_per_pass,
            swap_window=swap_window,
            # The construction step below orders trips by area, not by
            # urgency, so 2-swap's trip.index-based priority heuristic
            # would "fix" misorderings that aren't real - area only.
            swap_w_priority=0.0,
        )
        self._builder = ClusterFirstAlgorithm(
            "balanced-search-init",
            packer="best-fit",
            decreasing=True,
            by_priority=True,
            merge_leftovers=True,
            min_keep_utilization=0.9,
            order_by_urgency=True,
        )

    def _initial_solution(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        return self._builder.group(deliveries, capacity)
