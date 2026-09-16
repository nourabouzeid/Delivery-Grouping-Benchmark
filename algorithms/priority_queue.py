"""
Orders deliveries purely by priority (lower number = more urgent) before
packing them into trips, so urgent deliveries land in the earliest trips.

Ties (multiple deliveries sharing the same priority) are broken by their
original input order.
"""

import heapq
from itertools import count
from typing import List

from algorithms.base import GroupingAlgorithm
from models import Delivery, Trip


class PriorityQueueAlgorithm(GroupingAlgorithm):
    name = "priority-queue"

    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        counter = count()
        heap = [(d.priority, next(counter), d) for d in deliveries]
        heapq.heapify(heap)

        ordered: List[Delivery] = []
        while heap:
            _, _, delivery = heapq.heappop(heap)
            ordered.append(delivery)

        return self._first_fit_pack(ordered, capacity)
