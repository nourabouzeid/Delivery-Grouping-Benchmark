"""
First Fit Decreasing: sort by weight (heaviest first), then classic First Fit.

Standalone bin-packing baseline — no area or priority logic.
"""

from typing import List

from algorithms.base import GroupingAlgorithm
from algorithms.packing import first_fit, pack_ordered
from models import Delivery, Trip


class FFDAlgorithm(GroupingAlgorithm):
    name = "ffd"

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        return pack_ordered(deliveries, capacity, first_fit, decreasing=True)
