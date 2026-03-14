import asyncio
from collections import defaultdict
from typing import Any, Dict, Set

Topic = str
Subscriber = asyncio.Queue
Registry = Dict[Topic, Set[Subscriber]]


class PubSub:
    def __init__(self):
        self._topics: Registry = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, subscriber: asyncio.Queue, topic: str):
        """Subscribe caller to a topic."""
        async with self._lock:
            self._topics[topic].add(subscriber)

    async def unsubscribe(self, subscriber: asyncio.Queue, topic: str):
        """Unsubscribe a specific queue from a topic."""
        async with self._lock:
            self._topics[topic].discard(subscriber)
            # Delete topic if no listeners left
            if not self._topics[topic]:
                del self._topics[topic]

    async def broadcast(self, topic: str, message: Any):
        """Broadcast a message to all subscribers of a topic."""
        async with self._lock:
            queues = list(self._topics.get(topic, set()))
        for q in queues:
            try:
                q.put_nowait((topic, message))
            except asyncio.QueueFull:
                # Handle slow consumers – you might want to drop or log
                pass

    async def broadcast_from(self, publisher: asyncio.Queue, topic: str, message: Any):
        """Broadcast to all subscribers except the given queue."""
        async with self._lock:
            queues = [q for q in self._topics.get(topic, set()) if q is not publisher]
        for q in queues:
            try:
                q.put_nowait((topic, message))
            except asyncio.QueueFull:
                pass
