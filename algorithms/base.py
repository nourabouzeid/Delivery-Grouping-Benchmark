from abc import ABC, abstractmethod
from typing import List

from models import Delivery, Trip


class GroupingAlgorithm(ABC):
    """Base class for all trip-grouping strategies."""

    name: str = "unnamed-algorithm"

    @abstractmethod
    def group(self, deliveries: List[Delivery], capacity: float) -> List[Trip]:
        raise NotImplementedError

    @staticmethod
    def _new_trip(trips: List[Trip]) -> Trip:
        trip = Trip(index=len(trips))
        trips.append(trip)
        return trip

    @staticmethod
    def _first_fit_pack(ordered_deliveries: List[Delivery], capacity: float) -> List[Trip]:
        """
        Shared helper: greedily pack deliveries, in the given order, into
        trips using first-fit (try current trip, else open a new one).
        """
        trips: List[Trip] = []
        current: Trip = None
        for delivery in ordered_deliveries:
            if current is None or not current.can_fit(delivery, capacity):
                current = GroupingAlgorithm._new_trip(trips)
            current.add(delivery)
        return trips
