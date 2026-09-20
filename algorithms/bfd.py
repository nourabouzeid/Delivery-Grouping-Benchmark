"""
Best Fit Decreasing: sort by weight (heaviest first), then classic Best Fit.

Standalone bin-packing baseline — no area or priority logic.
"""

from typing import List

from algorithms.base import GroupingAlgorithm
from algorithms.packing import best_fit, pack_ordered
from models import Delivery, Trip


class BFDAlgorithm(GroupingAlgorithm):
    name = "bfd"

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        return pack_ordered(deliveries, capacity, best_fit, decreasing=True)
