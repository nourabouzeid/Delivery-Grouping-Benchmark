"""
Deliveries are packed into trips strictly in the order they were read
from the CSV.
"""

from typing import List

from algorithms.base import GroupingAlgorithm
from models import Delivery, Trip


class DummySequentialAlgorithm(GroupingAlgorithm):
    name = "dummy-sequential"

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        return self._first_fit_pack(deliveries, capacity)
