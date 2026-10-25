"""A small bounded cache for what the UI derives from immutable data (datasets never change
and their ids are never reused), kept per app on ``app.state``."""

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable


class LruCache:
    """At most ``size`` values, least recently used dropped first. A value is computed outside
    the lock, so two requests may compute the same one; either result is kept."""

    def __init__(self, size: int):
        self.size = size
        self._items: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(
        self,
        key: Hashable,
        compute: Callable[[], object],
        keep: Callable[[object], bool] | None = None,
    ):
        """The value of ``key``, computed if missing. A computed value that ``keep`` refuses
        is returned without being kept, so the next call computes it again."""
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key]
        value = compute()
        if keep is not None and not keep(value):
            return value
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self.size:
                self._items.popitem(last=False)
        return value

    def __len__(self) -> int:
        return len(self._items)
