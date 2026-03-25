import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List


class EventBus:
    _listeners: Dict[str, List[Callable[..., Coroutine]]] = defaultdict(list)

    @classmethod
    def register(cls, event_name: str, handler: Callable[..., Coroutine]):
        cls._listeners[event_name].append(handler)

    @classmethod
    async def emit(cls, event_name: str, payload: Any):
        for handler in cls._listeners.get(event_name, []):
            try:
                await handler(payload)
            except Exception:
                pass

    @classmethod
    def clear(cls):
        cls._listeners.clear()


event_bus = EventBus()
