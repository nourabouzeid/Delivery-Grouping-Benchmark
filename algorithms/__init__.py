"""
Algorithm registry - add new strategies here and they automatically show
up in benchmarks run via main.py --all.
"""

from algorithms.bfd import BFDAlgorithm
from algorithms.bfd_area import BFDAreaAlgorithm
from algorithms.cluster import (
    ClusterAreaAlgorithm,
    ClusterBFDAlgorithm,
    ClusterBFDMixAlgorithm,
    ClusterFFDAlgorithm,
    ClusterFFDMixAlgorithm,
    ClusterFirstAlgorithm,
    ClusterPriorityBFDAlgorithm,
    ClusterPriorityBFDMixAlgorithm,
    ClusterPriorityFFDAlgorithm,
    ClusterPriorityFFDMixAlgorithm,
)
from algorithms.balanced_search import BalancedSearchAlgorithm
from algorithms.ffd import FFDAlgorithm
from algorithms.first_fit import FirstFitAlgorithm
from algorithms.local_search import LocalSearchAlgorithm
from algorithms.priority_queue import PriorityQueueAlgorithm
from algorithms.regret_insertion import RegretInsertionAlgorithm
from algorithms.weighted_heuristic import WeightedHeuristicAlgorithm

ALL_ALGORITHMS = [
    FirstFitAlgorithm(),
    PriorityQueueAlgorithm(),
    FFDAlgorithm(),
    BFDAlgorithm(),
    BFDAreaAlgorithm(),
    ClusterAreaAlgorithm(),
    ClusterFFDAlgorithm(),
    ClusterBFDAlgorithm(),
    ClusterFFDMixAlgorithm(),
    ClusterBFDMixAlgorithm(),
    ClusterPriorityFFDAlgorithm(),
    ClusterPriorityBFDAlgorithm(),
    ClusterPriorityFFDMixAlgorithm(),
    ClusterPriorityBFDMixAlgorithm(),
    WeightedHeuristicAlgorithm(),
    RegretInsertionAlgorithm(),
    LocalSearchAlgorithm(),
    BalancedSearchAlgorithm(),
]

__all__ = [
    "ALL_ALGORITHMS",
    "BalancedSearchAlgorithm",
    "BFDAlgorithm",
    "BFDAreaAlgorithm",
    "ClusterAreaAlgorithm",
    "ClusterBFDAlgorithm",
    "ClusterBFDMixAlgorithm",
    "ClusterFFDAlgorithm",
    "ClusterFFDMixAlgorithm",
    "ClusterFirstAlgorithm",
    "ClusterPriorityBFDAlgorithm",
    "ClusterPriorityBFDMixAlgorithm",
    "ClusterPriorityFFDAlgorithm",
    "ClusterPriorityFFDMixAlgorithm",
    "FFDAlgorithm",
    "FirstFitAlgorithm",
    "LocalSearchAlgorithm",
    "PriorityQueueAlgorithm",
    "RegretInsertionAlgorithm",
    "WeightedHeuristicAlgorithm",
]
