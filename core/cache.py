"""A bounded LRU, and the order to render neighbours in so flipping stays instant."""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Callable


class LRUCache:
    """Thread-safe least-recently-used cache. `weigh` lets capacity mean bytes, not items."""

    def __init__(self, capacity: int, weigh: Callable[[object], int] = lambda _: 1) -> None:
        self.capacity = capacity
        self._weigh = weigh
        self._items: OrderedDict[object, object] = OrderedDict()
        self._total = 0
        self._lock = threading.Lock()

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._items

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def get(self, key: object) -> object | None:
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key: object, value: object) -> None:
        with self._lock:
            if key in self._items:
                self._total -= self._weigh(self._items.pop(key))
            self._items[key] = value
            self._total += self._weigh(value)
            # Always keeps the newest item, even one heavier than the whole budget.
            while self._total > self.capacity and len(self._items) > 1:
                _, evicted = self._items.popitem(last=False)
                self._total -= self._weigh(evicted)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._total = 0


def prefetch_order(
    index: int, count: int, direction: int = 1, ahead: int = 4, behind: int = 2
) -> list[int]:
    """Indices to render around the cursor, nearest first and favouring the travel direction.

    Holding a key consumes index+1 long before index-1, so the workers start there.
    The list wraps, because flipping does. The cursor itself is not included.
    """
    if count <= 1:
        return []
    out: list[int] = []
    for distance in range(1, max(ahead, behind) + 1):
        steps = []
        if distance <= ahead:
            steps.append(distance * direction)
        if distance <= behind:
            steps.append(-distance * direction)
        for step in steps:
            candidate = (index + step) % count
            if candidate != index and candidate not in out:
                out.append(candidate)
    return out
