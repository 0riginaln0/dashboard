"""
PubSub Module - A topic-based publish-subscribe system for asyncio applications.

```
import asyncio
from pubsub import PubSub
import pytest

async def test_pubsub():
    pubsub = PubSub()

    # Create subscriber queues
    queue_alerts = asyncio.Queue()
    queue_news = asyncio.Queue()
    queue_all = asyncio.Queue()          # listens to multiple topics
    queue_publisher = asyncio.Queue()
    queue_slow = asyncio.Queue(maxsize=1) # will demonstrate dropped messages

    # Subscribe to topics
    await pubsub.subscribe(queue_alerts, "alerts")
    await pubsub.subscribe(queue_news, "news")
    await pubsub.subscribe(queue_all, "alerts", "news", "sports", "chat")
    await pubsub.subscribe(queue_publisher, "chat")
    await pubsub.subscribe(queue_slow, "alerts")

    # 1. Broadcast to a single topic
    await pubsub.broadcast("System alert!", "alerts")

    # queue_alerts should receive it
    topic, msg = await queue_alerts.get()
    assert topic == "alerts"
    assert msg == "System alert!"

    # queue_all should receive it
    topic, msg = await queue_all.get()
    assert topic == "alerts"
    assert msg == "System alert!"

    # queue_slow should receive it
    topic, msg = await queue_slow.get()
    assert topic == "alerts"
    assert msg == "System alert!"

    # 2. Broadcast to multiple topics
    await pubsub.broadcast("Score update", "news", "sports")

    # queue_news receives the news message
    topic, msg = await queue_news.get()
    assert topic == "news"
    assert msg == "Score update"

    # queue_all receives both messages
    received = []
    for _ in range(2):
        topic, msg = await queue_all.get()
        received.append((topic, msg))
    expected_msgs = {("news", "Score update"), ("sports", "Score update")}
    assert set(received) == expected_msgs

    # 3. Broadcast from a publisher (exclude itself)
    await pubsub.broadcast_from(queue_publisher, "Hello everyone!", "chat")

    # queue_all receives it
    topic, msg = await queue_all.get()
    assert topic == "chat"
    assert msg == "Hello everyone!"

    # queue_publisher should NOT receive it
    with pytest.raises(asyncio.TimeoutError):  # or use try/except if not using pytest
        await asyncio.wait_for(queue_publisher.get(), timeout=0.1)

    # 4. Unsubscribe and verify no further messages
    await pubsub.unsubscribe(queue_news, "news")
    await pubsub.broadcast("Late news", "news")

    # queue_news should NOT receive anything
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue_news.get(), timeout=0.1)

    # queue_all still receives because it's still subscribed
    topic, msg = await queue_all.get()
    assert topic == "news"
    assert msg == "Late news"

    # 5. Slow consumer misses messages
    await pubsub.broadcast("System alert 1", "alerts")
    await pubsub.broadcast("System alert 2", "alerts")
    await pubsub.broadcast("System alert 3", "alerts")

    # queue_alerts receives all three
    for i in range(1, 4):
        topic, msg = await asyncio.wait_for(queue_alerts.get(), timeout=0.1)
        assert topic == "alerts"
        assert msg == f"System alert {i}"

    # queue_slow receives only the first alert (the rest are dropped because its queue is full)
    topic, msg = await queue_slow.get()
    assert topic == "alerts"
    assert msg == "System alert 1"

    # No second message arrives
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue_slow.get(), timeout=0.1)

    print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_pubsub())
```
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
            await pubsub.broadcast("Hello world!", "greetings")
            # Subscribers receive: ("greetings", "Hello world!")

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
            publisher_queue = asyncio.Queue()
            chat_queue = asyncio.Queue()
            await pubsub.subscribe(publisher_queue, "chat")
            await pubsub.subscribe(chat, "chat")

            await pubsub.broadcast_from(
                publisher_queue,
                "User joined the channel",
                "chat"
            )
            # chat_queue receives ("chat", "User joined the channel")
            # publisher_queue doesn't receive this message
            ```
        """
        topic_subscribers = []
        async with self._lock:
            for topic in topics:
                subscribers = [
                    s for s in self._topics.get(topic, set()) if s is not publisher
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
