"""
Algorithm registry - add new strategies here and they automatically show
up in benchmarks run via main.py --all.
"""

from algorithms.dummy import DummySequentialAlgorithm
from algorithms.priority_queue import PriorityQueueAlgorithm

ALL_ALGORITHMS = [
    DummySequentialAlgorithm(),
    PriorityQueueAlgorithm(),
]

__all__ = ["ALL_ALGORITHMS", "DummySequentialAlgorithm", "PriorityQueueAlgorithm"]
