"""Lightweight event bus for domain event dispatching.

Simple in-process pub/sub for decoupling components.
Not a distributed message queue — just clean separation of concerns.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[[Any], None]


class EventBus:
    """Simple synchronous event bus.

    Usage:
        bus = EventBus()
        bus.subscribe(DocumentCorrected, on_doc_corrected)
        bus.publish(DocumentCorrected(input_path="...", output_path="...", report={}))
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: EventHandler) -> None:
        """Remove a handler for a specific event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def publish(self, event: Any) -> None:
        """Publish an event to all registered handlers."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event_type.__name__}: {e}")

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()

    @property
    def handler_count(self) -> int:
        """Return total number of registered handlers."""
        return sum(len(h) for h in self._handlers.values())
