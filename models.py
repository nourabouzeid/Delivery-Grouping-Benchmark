from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class Delivery:
    """A single, already-validated delivery request."""
    id: str
    area: str
    priority: int          # lower number = more urgent
    weight: float           # kg

@dataclass
class Trip:
    """A single vehicle trip: an ordered bag of deliveries."""
    index: int
    deliveries: List[Delivery] = field(default_factory=list)
    total_weight: float = 0.0

    def __post_init__(self) -> None:
        if self.deliveries and self.total_weight == 0.0:
            self.total_weight = sum(d.weight for d in self.deliveries)

    @property
    def areas(self) -> Set[str]:
        return {d.area for d in self.deliveries}

    def remaining_capacity(self, capacity: float) -> float:
        return capacity - self.total_weight

    def can_fit(self, delivery: Delivery, capacity: float) -> bool:
        return self.total_weight + delivery.weight <= capacity + 1e-9

    def add(self, delivery: Delivery) -> None:
        self.deliveries.append(delivery)
        self.total_weight += delivery.weight

    def __repr__(self) -> str:
        ids = [d.id for d in self.deliveries]
        return (f"Trip(#{self.index}, weight={self.total_weight:.2f}kg, "
                f"areas={sorted(self.areas)}, deliveries={ids})")


@dataclass
class RejectedDelivery:
    """A row from the input that could not become a valid Delivery."""
    raw: dict
    reason: str

    def __repr__(self) -> str:
        return f"RejectedDelivery(raw={self.raw}, reason={self.reason!r})"
