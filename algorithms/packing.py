"""
Shared bin-packing primitives.

True First Fit / Best Fit scan every open trip (unlike the next-fit helper
on GroupingAlgorithm, which only tries the current trip). Lookups use a
segment tree / AVL index so packing stays O(n log n) instead of scanning
every trip for every delivery.
"""

import bisect
from collections import OrderedDict
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from models import Delivery, Trip

PackFn = Callable[[Sequence[Delivery], float], List[Trip]]

_EPS = 1e-9


def reindex_trips(trips: Iterable[Trip]) -> List[Trip]:
    """Return a new list of trips numbered 0..n-1, preserving contents."""
    reindexed: List[Trip] = []
    for i, trip in enumerate(trips):
        reindexed.append(
            Trip(index=i, deliveries=list(trip.deliveries), total_weight=trip.total_weight)
        )
    return reindexed


def order_trips_by_urgency(trips: Iterable[Trip]) -> List[Trip]:
    """
    Reorder trips so more urgent trips are dispatched first, then renumber.

    The priority-adherence metric only looks at trip *index*, and a trip is an
    atomic unit, so the order trips are dispatched in is a free lever: it
    changes the priority score without touching trip count, utilization, or
    which deliveries share a vehicle (and therefore without touching the area
    score either). Trips are sorted by mean priority of their contents, with
    the most urgent delivery as a tiebreak.
    """
    def key(trip: Trip):
        ps = [d.priority for d in trip.deliveries]
        if not ps:
            return (float("inf"), float("inf"))
        return (sum(ps) / len(ps), min(ps))

    return reindex_trips(sorted(trips, key=key))


def sort_deliveries(
    deliveries: Sequence[Delivery],
    *,
    by_priority: bool = False,
    decreasing: bool = False,
) -> List[Delivery]:
    """
    Stable sort. Priority ascending (more urgent first) is the primary key
    when requested; decreasing weight is the next key (classic FFD/BFD).
    """
    if not by_priority and not decreasing:
        return list(deliveries)

    def key(d: Delivery):
        parts = []
        if by_priority:
            parts.append(d.priority)
        if decreasing:
            parts.append(-d.weight)
        return tuple(parts)

    return sorted(deliveries, key=key)


def group_by_area(deliveries: Sequence[Delivery]) -> List[Tuple[str, List[Delivery]]]:
    """Partition deliveries by area, preserving first-seen area order and input order within each area."""
    groups: OrderedDict[str, List[Delivery]] = OrderedDict()
    for delivery in deliveries:
        groups.setdefault(delivery.area, []).append(delivery)
    return list(groups.items())


class _MaxSegTree:
    """Point-assign remaining capacities; query leftmost index with remaining >= need."""

    def __init__(self, n: int):
        size = 1
        while size < max(1, n):
            size *= 2
        self.size = size
        self.tree = [0.0] * (2 * size)

    def update(self, i: int, value: float) -> None:
        i += self.size
        self.tree[i] = value
        i //= 2
        while i:
            self.tree[i] = max(self.tree[i * 2], self.tree[i * 2 + 1])
            i //= 2

    def leftmost_at_least(self, need: float) -> int:
        if self.tree[1] + _EPS < need:
            return -1
        i = 1
        size = self.size
        while i < size:
            left = i * 2
            if self.tree[left] + _EPS >= need:
                i = left
            else:
                i = left + 1
        return i - size


class _AVLNode:
    __slots__ = ("key", "left", "right", "height")

    def __init__(self, key: Tuple[float, int]):
        self.key = key
        self.left: Optional["_AVLNode"] = None
        self.right: Optional["_AVLNode"] = None
        self.height = 1


def _avl_height(node: Optional[_AVLNode]) -> int:
    return node.height if node else 0


def _avl_update(node: _AVLNode) -> _AVLNode:
    node.height = 1 + max(_avl_height(node.left), _avl_height(node.right))
    return node


def _avl_rotate_left(node: _AVLNode) -> _AVLNode:
    right = node.right
    node.right = right.left
    right.left = node
    _avl_update(node)
    return _avl_update(right)


def _avl_rotate_right(node: _AVLNode) -> _AVLNode:
    left = node.left
    node.left = left.right
    left.right = node
    _avl_update(node)
    return _avl_update(left)


def _avl_balance(node: _AVLNode) -> _AVLNode:
    _avl_update(node)
    bf = _avl_height(node.left) - _avl_height(node.right)
    if bf > 1:
        if _avl_height(node.left.right) > _avl_height(node.left.left):
            node.left = _avl_rotate_left(node.left)
        return _avl_rotate_right(node)
    if bf < -1:
        if _avl_height(node.right.left) > _avl_height(node.right.right):
            node.right = _avl_rotate_right(node.right)
        return _avl_rotate_left(node)
    return node


def _avl_insert(node: Optional[_AVLNode], key: Tuple[float, int]) -> _AVLNode:
    if node is None:
        return _AVLNode(key)
    if key < node.key:
        node.left = _avl_insert(node.left, key)
    else:
        node.right = _avl_insert(node.right, key)
    return _avl_balance(node)


def _avl_min(node: _AVLNode) -> _AVLNode:
    while node.left is not None:
        node = node.left
    return node


def _avl_delete(node: Optional[_AVLNode], key: Tuple[float, int]) -> Optional[_AVLNode]:
    if node is None:
        return None
    if key < node.key:
        node.left = _avl_delete(node.left, key)
    elif key > node.key:
        node.right = _avl_delete(node.right, key)
    else:
        if node.left is None:
            return node.right
        if node.right is None:
            return node.left
        succ = _avl_min(node.right)
        node.key = succ.key
        node.right = _avl_delete(node.right, succ.key)
    return _avl_balance(node)


def _avl_lower_bound(node: Optional[_AVLNode], key: Tuple[float, int]) -> Optional[_AVLNode]:
    best = None
    while node is not None:
        if node.key >= key:
            best = node
            node = node.left
        else:
            node = node.right
    return best


def _trips_from_bins(
    contents: List[List[Delivery]],
    remaining: List[float],
    n_bins: int,
    capacity: float,
) -> List[Trip]:
    trips: List[Trip] = []
    for i in range(n_bins):
        trips.append(
            Trip(
                index=i,
                deliveries=contents[i],
                total_weight=capacity - remaining[i],
            )
        )
    return trips


def first_fit(ordered_deliveries: Sequence[Delivery], capacity: float) -> List[Trip]:
    """Place each delivery in the earliest trip that can take it; else open a new trip."""
    n = len(ordered_deliveries)
    if n == 0:
        return []

    tree = _MaxSegTree(n)
    total = [0.0] * n
    remaining = [0.0] * n
    contents: List[List[Delivery]] = [[] for _ in range(n)]
    n_bins = 0

    for delivery in ordered_deliveries:
        idx = tree.leftmost_at_least(delivery.weight)
        if idx < 0:
            idx = n_bins
            n_bins += 1
        total[idx] += delivery.weight
        remaining[idx] = capacity - total[idx]
        contents[idx].append(delivery)
        tree.update(idx, remaining[idx])

    return _trips_from_bins(contents, remaining, n_bins, capacity)


def best_fit(ordered_deliveries: Sequence[Delivery], capacity: float) -> List[Trip]:
    """
    Place each delivery in the feasible trip with the least leftover capacity
    after the placement. Open a new trip only when nothing fits.
    Ties break toward the earliest trip (same as a left-to-right scan).
    """
    n = len(ordered_deliveries)
    if n == 0:
        return []

    total = [0.0] * n
    remaining = [0.0] * n
    contents: List[List[Delivery]] = [[] for _ in range(n)]
    n_bins = 0
    root: Optional[_AVLNode] = None

    for delivery in ordered_deliveries:
        node = _avl_lower_bound(root, (delivery.weight - _EPS, -1))
        if node is None:
            idx = n_bins
            n_bins += 1
            total[idx] = delivery.weight
            remaining[idx] = capacity - total[idx]
            contents[idx].append(delivery)
            root = _avl_insert(root, (remaining[idx], idx))
            continue
        _, idx = node.key
        root = _avl_delete(root, node.key)
        total[idx] += delivery.weight
        remaining[idx] = capacity - total[idx]
        contents[idx].append(delivery)
        root = _avl_insert(root, (remaining[idx], idx))

    return _trips_from_bins(contents, remaining, n_bins, capacity)


def pack_by_area_with_leftovers(
    deliveries: Sequence[Delivery],
    capacity: float,
    pack: PackFn,
    *,
    min_keep_utilization: float = 0.95,
    order_by_urgency: bool = True,
) -> List[Trip]:
    """
    Generic cluster-first driver: run any constructor `pack` inside each area,
    keep trips that are already (nearly) full, and re-pack the underfilled
    fragments together across areas with the same constructor.

    This lets constructors whose placement rule is more elaborate than plain
    FFD/BFD (weighted scoring, regret insertion, ...) get area-pure trips
    without giving up their own decision logic.
    """
    kept: List[Trip] = []
    leftovers: List[Delivery] = []
    for _, items in group_by_area(deliveries):
        for trip in pack(items, capacity):
            if is_full_trip(trip, capacity, min_keep_utilization):
                kept.append(trip)
            else:
                leftovers.extend(trip.deliveries)
    if leftovers:
        kept.extend(pack(leftovers, capacity))
    return order_trips_by_urgency(kept) if order_by_urgency else reindex_trips(kept)


def _quantum(deliveries: Sequence[Delivery]) -> float:
    """
    Largest power-of-ten step (1, 0.1, 0.01 ...) that every weight is a whole
    multiple of, so leftovers can be bucketed exactly as integers. Falls back
    to 1e-6 for arbitrary floats (still correct, just more buckets).
    """
    for step in (1.0, 0.1, 0.01, 0.001, 1e-4, 1e-5, 1e-6):
        if all(abs(d.weight / step - round(d.weight / step)) < 1e-7 for d in deliveries):
            return step
    return 1e-6


def best_fit_area_affine(
    ordered_deliveries: Sequence[Delivery],
    capacity: float,
    *,
    slack: float = 2.0,
) -> List[Trip]:
    """
    Best Fit that breaks ties (and near-ties) toward a trip already carrying
    the delivery's area.

    Plain Best Fit picks the tightest feasible trip and, when several trips
    are exactly equally tight, picks arbitrarily. On real weight grids (e.g.
    0.1 kg) that tie set is huge, so choosing among the ties by area is free:
    same trip count and utilization, better area grouping. `slack` (in units of
    the weight grid) widens "tie" to "within a few grid steps of tightest",
    which buys more area grouping for a negligible utilization cost.

    Trips are bucketed by integer leftover, so a lookup touches only the few
    distinct leftover values inside the slack window, never every trip.
    """
    n = len(ordered_deliveries)
    if n == 0:
        return []

    step = _quantum(ordered_deliveries)
    q = lambda x: int(round(x / step))
    cap_q = q(capacity)
    slack_q = int(round(slack))

    trips: List[Trip] = []
    left_q: List[int] = []                       # trip idx -> leftover in quanta
    by_left: dict = {}                           # leftover -> {"*": [idx], area: [idx]}
    keys: List[int] = []                         # sorted leftovers with >=1 live trip
    live: dict = {}                              # leftover -> count of live trips

    def register(idx: int) -> None:
        k = left_q[idx]
        bucket = by_left.setdefault(k, {})
        bucket.setdefault("*", []).append(idx)
        for a in trips[idx].areas:
            bucket.setdefault(a, []).append(idx)
        if live.get(k, 0) == 0:
            bisect.insort(keys, k)
        live[k] = live.get(k, 0) + 1

    def unregister_key(k: int) -> None:
        live[k] -= 1
        if live[k] == 0:
            keys.remove(k)

    def pop_valid(lst: Optional[List[int]], k: int) -> Optional[int]:
        # Entries go stale when a trip's leftover changes; validate lazily.
        while lst:
            c = lst.pop()
            if left_q[c] == k:
                return c
        return None

    for d in ordered_deliveries:
        need = q(d.weight)
        i = bisect.bisect_left(keys, need)
        if i == len(keys):
            trip = Trip(index=len(trips))
            trips.append(trip)
            left_q.append(cap_q)
            trip.add(d)
            left_q[-1] = cap_q - q(trip.total_weight)
            register(len(trips) - 1)
            continue

        tight = keys[i]
        chosen_k, idx = tight, None
        j = i
        while j < len(keys) and keys[j] <= tight + slack_q:
            k = keys[j]
            c = pop_valid(by_left[k].get(d.area), k)
            if c is not None:
                idx, chosen_k = c, k
                break
            j += 1
        if idx is None:
            idx = pop_valid(by_left[tight]["*"], tight)

        unregister_key(chosen_k)
        trip = trips[idx]
        trip.add(d)
        left_q[idx] = cap_q - q(trip.total_weight)
        register(idx)

    return trips


def redistribute_priorities(trips: Iterable[Trip]) -> List[Trip]:
    """
    Capacity-neutral priority consolidation.

    Two deliveries of identical weight are interchangeable as far as vehicle
    capacity is concerned, so their trip assignments can be exchanged freely.
    Within each group of trips that share the same area set, this re-deals
    deliveries of equal weight so the most urgent ones land in the trips that
    will be dispatched earliest.

    Every trip keeps exactly its old total weight, its old set of areas, and
    its old number of deliveries, so trip count, utilization and area score
    are provably unchanged; only *which* equal-weight delivery sits where
    moves, which is what lifts the priority score of tightly-packed (priority
    blind) solutions.

    Returns new Trip objects; the inputs are not modified. Trips are
    returned in most-urgent-first order (renumbered), ready to dispatch.
    """
    fresh = [
        Trip(index=t.index, deliveries=list(t.deliveries), total_weight=t.total_weight)
        for t in trips
    ]

    def mean_priority(t: Trip) -> float:
        return sum(d.priority for d in t.deliveries) / len(t.deliveries) if t.deliveries else float("inf")

    groups: dict = {}
    for t in fresh:
        groups.setdefault(frozenset(t.areas), []).append(t)

    for group in groups.values():
        group.sort(key=mean_priority)
        slots: dict = {}
        for pos, t in enumerate(group):
            for i, d in enumerate(t.deliveries):
                slots.setdefault(d.weight, []).append((pos, i))
        for weight_slots in slots.values():
            weight_slots.sort()  # earliest-dispatched trips first
            items = sorted(
                (group[p].deliveries[i] for p, i in weight_slots),
                key=lambda d: d.priority,
            )
            for (p, i), d in zip(weight_slots, items):
                group[p].deliveries[i] = d

    return order_trips_by_urgency(fresh)


def pack_ordered(
    deliveries: Sequence[Delivery],
    capacity: float,
    packer: PackFn,
    *,
    by_priority: bool = False,
    decreasing: bool = False,
) -> List[Trip]:
    ordered = sort_deliveries(deliveries, by_priority=by_priority, decreasing=decreasing)
    return packer(ordered, capacity)


def is_full_trip(trip: Trip, capacity: float, min_keep_utilization: float) -> bool:
    if capacity <= 0:
        return True
    return (trip.total_weight / capacity) + _EPS >= min_keep_utilization
