from abc import abstractmethod
from typing import Any


class RapidataFilter:
    """The base class for all Rapidata Filters."""

    @abstractmethod
    def _to_model(self) -> Any:
        pass

    def __or__(self, other):
        """Enable the | operator to create OrFilter combinations."""
        if not isinstance(other, RapidataFilter):
            return NotImplemented
        
        from rapidata.rapidata_client.filter.or_filter import OrFilter
        
        # If self is already an OrFilter, extend its filters list
        if isinstance(self, OrFilter):
            if isinstance(other, OrFilter):
                return OrFilter(self.filters + other.filters)
            else:
                return OrFilter(self.filters + [other])
        # If other is an OrFilter, prepend self to its filters
        elif isinstance(other, OrFilter):
            return OrFilter([self] + other.filters)
        # Neither is an OrFilter, create a new one
        else:
            return OrFilter([self, other])

    def __invert__(self):
        """Enable the ~ operator to create NotFilter negations."""
        from rapidata.rapidata_client.filter.not_filter import NotFilter
        
        # If self is already a NotFilter, return the original filter (double negation)
        if isinstance(self, NotFilter):
            return self.filter
        # Create a new NotFilter
        else:
            return NotFilter(self)
