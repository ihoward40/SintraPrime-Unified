"""
Event Filtering - Complex filtering and DSL for event selection.

Features:
- Filter expression DSL
- Complex filtering rules
- Tag-based filtering
- Time range filtering
- Custom filter functions
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

from .event_hub import Event

logger = logging.getLogger(__name__)


class FilterOperator(str, Enum):
    """Filter comparison operators."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"


class LogicalOperator(str, Enum):
    """Logical operators for combining filters."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class EventFilter:
    """
    Single filter condition for events.
    
    Supports filtering on:
    - Event type
    - Source
    - Tags
    - Payload fields
    - Priority
    - Timestamps
    """
    field: str
    operator: FilterOperator
    value: Any
    
    def matches(self, event: Event) -> bool:
        """
        Check if event matches this filter.
        
        Args:
            event: Event to check
            
        Returns:
            True if event matches
        """
        # Get field value
        field_value = self._get_field_value(event)
        
        if field_value is None:
            return False
        
        # Apply operator
        if self.operator == FilterOperator.EQUALS:
            return field_value == self.value
        elif self.operator == FilterOperator.NOT_EQUALS:
            return field_value != self.value
        elif self.operator == FilterOperator.GREATER_THAN:
            return field_value > self.value
        elif self.operator == FilterOperator.LESS_THAN:
            return field_value < self.value
        elif self.operator == FilterOperator.GREATER_EQUAL:
            return field_value >= self.value
        elif self.operator == FilterOperator.LESS_EQUAL:
            return field_value <= self.value
        elif self.operator == FilterOperator.IN:
            return field_value in self.value
        elif self.operator == FilterOperator.NOT_IN:
            return field_value not in self.value
        elif self.operator == FilterOperator.CONTAINS:
            return self.value in str(field_value)
        elif self.operator == FilterOperator.NOT_CONTAINS:
            return self.value not in str(field_value)
        elif self.operator == FilterOperator.STARTS_WITH:
            return str(field_value).startswith(self.value)
        elif self.operator == FilterOperator.ENDS_WITH:
            return str(field_value).endswith(self.value)
        elif self.operator == FilterOperator.REGEX:
            import re
            return bool(re.match(self.value, str(field_value)))
        
        return False
    
    def _get_field_value(self, event: Event) -> Any:
        """
        Get field value from event.
        
        Supports nested paths like "payload.user.id"
        
        Args:
            event: Event to extract from
            
        Returns:
            Field value or None
        """
        parts = self.field.split(".")
        current = event
        
        for part in parts:
            if part == "payload" and hasattr(current, "payload"):
                current = current.payload
            elif part == "tags" and hasattr(current, "tags"):
                current = current.tags
            elif isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        
        return current


class FilterEngine:
    """
    Advanced filter engine with DSL support.
    
    Supports complex filtering with AND/OR/NOT logic.
    """
    
    def __init__(self):
        """Initialize filter engine."""
        self.filters: List[Union[EventFilter, 'FilterEngine']] = []
        self.operator = LogicalOperator.AND
        self.custom_filters: Dict[str, Callable] = {}
    
    def add_filter(self, field: str, operator: FilterOperator, value: Any) -> 'FilterEngine':
        """
        Add a filter condition.
        
        Args:
            field: Field to filter on
            operator: Comparison operator
            value: Value to compare
            
        Returns:
            Self for chaining
        """
        self.filters.append(EventFilter(field, operator, value))
        return self
    
    def add_tag_filter(self, tag: str, present: bool = True) -> 'FilterEngine':
        """
        Add tag-based filter.
        
        Args:
            tag: Tag to filter on
            present: If True, event must have tag
            
        Returns:
            Self for chaining
        """
        if present:
            self.filters.append(EventFilter(
                field="tags",
                operator=FilterOperator.CONTAINS,
                value=tag
            ))
        else:
            self.filters.append(EventFilter(
                field="tags",
                operator=FilterOperator.NOT_CONTAINS,
                value=tag
            ))
        return self
    
    def add_time_range_filter(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> 'FilterEngine':
        """
        Add time range filter.
        
        Args:
            start_time: Include events after this time
            end_time: Include events before this time
            
        Returns:
            Self for chaining
        """
        if start_time:
            self.filters.append(EventFilter(
                field="timestamp",
                operator=FilterOperator.GREATER_EQUAL,
                value=start_time.isoformat()
            ))
        
        if end_time:
            self.filters.append(EventFilter(
                field="timestamp",
                operator=FilterOperator.LESS_EQUAL,
                value=end_time.isoformat()
            ))
        
        return self
    
    def add_priority_filter(self, min_priority: int, max_priority: int) -> 'FilterEngine':
        """
        Add priority filter.
        
        Args:
            min_priority: Minimum priority
            max_priority: Maximum priority
            
        Returns:
            Self for chaining
        """
        if min_priority > 0:
            self.filters.append(EventFilter(
                field="priority",
                operator=FilterOperator.GREATER_EQUAL,
                value=min_priority
            ))
        
        if max_priority < 1:
            self.filters.append(EventFilter(
                field="priority",
                operator=FilterOperator.LESS_EQUAL,
                value=max_priority
            ))
        
        return self
    
    def add_custom_filter(self, name: str, filter_fn: Callable) -> 'FilterEngine':
        """
        Add custom filter function.
        
        Args:
            name: Filter name
            filter_fn: Function(event) -> bool
            
        Returns:
            Self for chaining
        """
        self.custom_filters[name] = filter_fn
        return self
    
    def and_filter(self) -> 'FilterEngine':
        """Set logical operator to AND."""
        self.operator = LogicalOperator.AND
        return self
    
    def or_filter(self) -> 'FilterEngine':
        """Set logical operator to OR."""
        self.operator = LogicalOperator.OR
        return self
    
    def matches(self, event: Event) -> bool:
        """
        Check if event matches all filters.
        
        Args:
            event: Event to check
            
        Returns:
            True if event matches filters
        """
        # Apply custom filters first
        for filter_fn in self.custom_filters.values():
            try:
                if not filter_fn(event):
                    return False
            except Exception as e:
                logger.error("Error in custom filter: %s", str(e))
                return False
        
        # Apply filter conditions
        if not self.filters:
            return True
        
        if self.operator == LogicalOperator.AND:
            return all(f.matches(event) for f in self.filters)
        elif self.operator == LogicalOperator.OR:
            return any(f.matches(event) for f in self.filters)
        
        return False
    
    def get_filter_count(self) -> int:
        """Get number of active filters."""
        return len(self.filters) + len(self.custom_filters)


class FilterBuilder:
    """Builder for creating complex filter expressions."""
    
    @staticmethod
    def event_type(event_type: str) -> EventFilter:
        """Filter by event type."""
        return EventFilter(
            field="event_type",
            operator=FilterOperator.EQUALS,
            value=event_type
        )
    
    @staticmethod
    def source(source: str) -> EventFilter:
        """Filter by source."""
        return EventFilter(
            field="source",
            operator=FilterOperator.EQUALS,
            value=source
        )
    
    @staticmethod
    def agent_id(agent_id: str) -> EventFilter:
        """Filter by agent ID."""
        return EventFilter(
            field="agent_id",
            operator=FilterOperator.EQUALS,
            value=agent_id
        )
    
    @staticmethod
    def has_tag(tag: str) -> EventFilter:
        """Filter events with specific tag."""
        return EventFilter(
            field="tags",
            operator=FilterOperator.CONTAINS,
            value=tag
        )
    
    @staticmethod
    def priority_is(priority: int) -> EventFilter:
        """Filter by priority."""
        return EventFilter(
            field="priority",
            operator=FilterOperator.EQUALS,
            value=priority
        )
    
    @staticmethod
    def high_priority() -> EventFilter:
        """Filter for high priority events."""
        return EventFilter(
            field="priority",
            operator=FilterOperator.GREATER_THAN,
            value=0
        )
    
    @staticmethod
    def payload_contains(key: str, value: Any) -> EventFilter:
        """Filter by payload field value."""
        return EventFilter(
            field=f"payload.{key}",
            operator=FilterOperator.EQUALS,
            value=value
        )
