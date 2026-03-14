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

    async def subscribe(self, subscriber: asyncio.Queue, *topics: str):
        async with self._lock:
            for topic in topics:
                self._topics[topic].add(subscriber)

    async def unsubscribe(self, subscriber: asyncio.Queue, *topics: str):
        async with self._lock:
            for topic in topics:
                subscribers = self._topics.get(topic)
                if subscribers is not None:
                    subscribers.discard(subscriber)
                    if not subscribers:
                        del self._topics[topic]

    async def broadcast(self, message: Any, *topics: str):
        topic_subscribers = []
        async with self._lock:
            for topic in topics:
                subscribers = list(self._topics.get(topic, set()))
                topic_subscribers.append((topic, subscribers))

        for topic, subscribers in topic_subscribers:
            for subscriber in subscribers:
                self._try_put_message(subscriber, topic, message)

    async def broadcast_from(
        self, publisher: asyncio.Queue, message: Any, *topics: str
    ):
        topic_subscribers = []
        async with self._lock:
            for topic in topics:
                subscribers = [
                    q for q in self._topics.get(topic, set()) if q is not publisher
                ]
                topic_subscribers.append((topic, subscribers))

        for topic, subscribers in topic_subscribers:
            for subscriber in subscribers:
                self._try_put_message(subscriber, topic, message)

    def _try_put_message(self, subscriber: asyncio.Queue, topic: str, message: Any):
        try:
            subscriber.put_nowait((topic, message))
        except asyncio.QueueFull, asyncio.QueueShutDown:
            # Handle slow consumers – you might want to drop or log
            pass
