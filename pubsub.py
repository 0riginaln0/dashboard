"""
PubSub Module - A lightweight, topic-based publish-subscribe system for asyncio applications.
"""

import asyncio
from collections import defaultdict
from typing import Any, Dict, Set

Topic = str
Subscriber = asyncio.Queue
Registry = Dict[Topic, Set[Subscriber]]


class PubSub:
    """
    A topic-based publish-subscribe system for asynchronous message passing.

    Attributes:
        _topics (Registry): Dictionary mapping topics to sets of subscriber queues
        _lock (asyncio.Lock): Lock for thread-safe operations on the registry

    Example:
        ```python
        pubsub = PubSub()

        # Multiple subscribers can listen to the same topic
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        await pubsub.subscribe(queue1, "alerts")
        await pubsub.subscribe(queue2, "alerts")

        # Broadcast to all subscribers
        await pubsub.broadcast("System alert!", "alerts")

        # First subscriber receives: ("alerts", "System alert!")
        # Second subscriber receives: ("alerts", "System alert!")
        ```
    """

    def __init__(self):
        self._topics: Registry = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, subscriber: asyncio.Queue, *topics: str):
        """
        Subscribe a queue to one or more topics.

        Args:
            subscriber (asyncio.Queue): The queue that will receive messages.
                This queue will receive messages as (topic, message) tuples.
            *topics (str): Variable number of topic strings to subscribe to.
                The subscriber will receive messages published to any of these topics.

        Example:
            ```python
            queue = asyncio.Queue()

            # Subscribe to single topic
            await pubsub.subscribe(queue, "temperature")

            # Subscribe to multiple topics
            await pubsub.subscribe(queue, "news", "weather", "sports")
            ```
        """
        async with self._lock:
            for topic in topics:
                self._topics[topic].add(subscriber)

    async def unsubscribe(self, subscriber: asyncio.Queue, *topics: str):
        """
        Unsubscribe a queue from one or more topics.

        Args:
            subscriber (asyncio.Queue): The queue to unsubscribe.
            *topics (str): Topics to unsubscribe from.

        Example:
            ```python
            # Unsubscribe from a single topic
            await pubsub.unsubscribe(queue, "weather")

            # Unsubscribe from multiple topics
            await pubsub.unsubscribe(queue, "news", "sports")
            ```
        """
        async with self._lock:
            for topic in topics:
                subscribers = self._topics.get(topic)
                if subscribers is not None:
                    subscribers.discard(subscriber)
                    if not subscribers:
                        del self._topics[topic]

    async def broadcast(self, message: Any, *topics: str):
        """
        Broadcast a message to all subscribers of the specified topics.

        Args:
            message (Any): The message to broadcast.
            *topics (str): Topics to broadcast to.

        Example:
            ```python
            # Broadcast simple string
            await pubsub.broadcast("Hello world!", "greetings")

            # Broadcast structured data to multiple topics
            data = {"sensor": "temperature", "value": 23.5, "unit": "celsius"}
            await pubsub.broadcast(data, "telemetry", "monitoring")

            # Subscribers receive: ("telemetry", data)
            #                      ("monitoring", data)
            ```

        Note:
            - Slow consumers may miss messages if their queue is full (see _try_put_message)
            - The broadcast is asynchronous - it doesn't wait for subscribers to process messages
        """
        topic_subscribers = []
        async with self._lock:
            for topic in topics:
                subscribers = list(self._topics.get(topic, set()))
                if subscribers:
                    topic_subscribers.append((topic, subscribers))

        for topic, subscribers in topic_subscribers:
            for subscriber in subscribers:
                self._try_put_message(subscriber, topic, message)

    async def broadcast_from(
        self, publisher: asyncio.Queue, message: Any, *topics: str
    ):
        """
        Broadcast a message to all subscribers except the publisher itself.

        Args:
            publisher (asyncio.Queue): The queue of the publisher to exclude.
                This subscriber will not receive the message.
            message (Any): The message to broadcast.
            *topics (str): Topics to broadcast to.

        Example:
            ```python
            # Publisher that also listens to its own topic
            publisher_queue = asyncio.Queue()
            await pubsub.subscribe(publisher_queue, "chat")

            # Broadcast to all other chat subscribers
            await pubsub.broadcast_from(
                publisher_queue,
                "User joined the channel",
                "chat"
            )
            # Publisher doesn't receive this message
            ```
        """
        topic_subscribers = []
        async with self._lock:
            for topic in topics:
                subscribers = [
                    q for q in self._topics.get(topic, set()) if q is not publisher
                ]
                if subscribers:
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
