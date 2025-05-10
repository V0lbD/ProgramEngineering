from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum
import time


# тип события в БД
class EventType(Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


# класс события БД
class DatabaseEvent:
    def __init__(self, event_type: EventType, table: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.table = table
        self.data = data
        self.timestamp = time.time()

    def __str__(self):
        return f"{self.timestamp}: {self.event_type.value} on {self.table} - {self.data}"


# абстрактный класс наблюдателя
class EventObserver(ABC):
    @abstractmethod
    def update(self, event: DatabaseEvent):
        pass


# посредник для управления наблюдателями
class EventMediator:
    def __init__(self):
        self._observers: Dict[EventType, List[EventObserver]] = {
            EventType.INSERT: [],
            EventType.UPDATE: [],
            EventType.DELETE: []
        }

    def subscribe(self, event_type: EventType, observer: EventObserver):
        self._observers[event_type].append(observer)

    def unsubscribe(self, event_type: EventType, observer: EventObserver):
        self._observers[event_type].remove(observer)

    def notify(self, event: DatabaseEvent):
        for observer in self._observers[event.event_type]:
            observer.update(event)


# агрегатор событий (имитация источника событий БД)
class DatabaseEventAggregator:
    def __init__(self):
        self.mediator = EventMediator()
        self._event_history: List[DatabaseEvent] = []

    def add_event(self, event: DatabaseEvent):
        print(f"New database event: {event}")
        self._event_history.append(event)
        self.mediator.notify(event)

    def get_event_history(self):
        return self._event_history.copy()


# реализация наблюдателей
class AuditLogger(EventObserver):
    def update(self, event: DatabaseEvent):
        print(f"[Audit Log] {event}")


class CacheInvalidator(EventObserver):
    def update(self, event: DatabaseEvent):
        print(f"[Cache] Invalidating cache for {event.table} due to {event.event_type.value}")


class ReplicationService(EventObserver):
    def update(self, event: DatabaseEvent):
        print(f"[Replication] Replicating {event.event_type.value} operation to standby database")


class AnalyticsService(EventObserver):
    def update(self, event: DatabaseEvent):
        print(f"[Analytics] Processing {event.event_type.value} event for analytics")


# пример использования
if __name__ == "__main__":
    # создаем агрегатор событий
    aggregator = DatabaseEventAggregator()

    # создаём и подписываем наблюдателей
    audit_logger = AuditLogger()
    cache_invalidator = CacheInvalidator()
    replication_service = ReplicationService()
    analytics_service = AnalyticsService()

    # подписываем наблюдателей на события
    mediator = aggregator.mediator
    mediator.subscribe(EventType.INSERT, audit_logger)
    mediator.subscribe(EventType.UPDATE, audit_logger)
    mediator.subscribe(EventType.DELETE, audit_logger)

    mediator.subscribe(EventType.UPDATE, cache_invalidator)
    mediator.subscribe(EventType.DELETE, cache_invalidator)

    mediator.subscribe(EventType.INSERT, replication_service)
    mediator.subscribe(EventType.UPDATE, replication_service)
    mediator.subscribe(EventType.DELETE, replication_service)

    mediator.subscribe(EventType.INSERT, analytics_service)

    # имитируем события БД
    aggregator.add_event(DatabaseEvent(
        EventType.INSERT,
        "users",
        {"id": 1, "name": "Abob Us", "email": "example@example.com"}
    ))

    aggregator.add_event(DatabaseEvent(
        EventType.UPDATE,
        "users",
        {"id": 1, "name": "Abib Us"}
    ))

    aggregator.add_event(DatabaseEvent(
        EventType.DELETE,
        "products",
        {"id": 42, "name": "example_product"}
    ))

    # выводим историю событий
    print("\nEvent history:")
    for event in aggregator.get_event_history():
        print(event)