import typing
from abc import ABC, abstractmethod


class ComparableDataStructure(ABC):
    """Base class for data structures that need equality and comparison methods."""

    @abstractmethod
    def _get_comparison_key(self) -> typing.Any:
        """Return the key used for comparison operations.

        This should return a hashable object that uniquely identifies
        the instance for equality comparisons.
        """
        pass

    def __eq__(self, other: typing.Any) -> bool:
        """Generic equality comparison using comparison key."""
        if not isinstance(other, self.__class__):
            return False
        return self._get_comparison_key() == other._get_comparison_key()

    def __ne__(self, other: typing.Any) -> bool:
        """Not equal comparison."""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Hash based on comparison key."""
        key = self._get_comparison_key()
        if isinstance(key, (list, dict)):
            # Convert unhashable types to hashable equivalents
            if isinstance(key, list):
                key = tuple(key)
            elif isinstance(key, dict):
                key = tuple(sorted(key.items()))
        return hash(key)


class OrderedDataStructure(ComparableDataStructure):
    """Base class for data structures that need ordering comparisons."""

    @abstractmethod
    def _get_ordering_key(self) -> typing.Any:
        """Return the key used for ordering operations.

        This should return a comparable object for sorting.
        """
        pass

    def __lt__(self, other) -> bool:
        """Less than comparison."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._get_ordering_key() < other._get_ordering_key()

    def __le__(self, other) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._get_ordering_key() <= other._get_ordering_key()

    def __gt__(self, other) -> bool:
        """Greater than comparison."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._get_ordering_key() > other._get_ordering_key()

    def __ge__(self, other) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._get_ordering_key() >= other._get_ordering_key()


class RepresentableDataStructure(ABC):
    """Base class for data structures that need consistent string representation."""

    @abstractmethod
    def _get_repr_attrs(self) -> typing.Dict[str, typing.Any]:
        """Return attributes to include in __repr__.

        Returns:
            Dict mapping attribute names to values for representation
        """
        pass

    def __repr__(self) -> str:
        """Generic representation showing class name and key attributes."""
        class_name = self.__class__.__name__
        attrs = self._get_repr_attrs()

        # Format attributes as key=value pairs
        attr_strs = []
        for key, value in attrs.items():
            # Handle special formatting for different types
            if isinstance(value, str):
                attr_strs.append(f"{key}={value!r}")
            elif isinstance(value, (list, tuple)) and len(value) > 3:
                # Truncate long sequences in repr
                truncated = list(value[:3]) + ["..."]
                attr_strs.append(f"{key}={truncated}")
            else:
                attr_strs.append(f"{key}={value!r}")

        attr_str = ", ".join(attr_strs)
        return f"{class_name}({attr_str})"


class DataStructureBase(ComparableDataStructure, RepresentableDataStructure):
    """Combination base class providing both comparison and representation methods."""

    pass


class UrlDataStructure(DataStructureBase):
    """Base class for URL-like data structures."""

    def __str__(self) -> str:
        """String representation should return the URL string."""
        return self._get_url_string()

    @abstractmethod
    def _get_url_string(self) -> str:
        """Return the URL as a string."""
        pass

    def _get_comparison_key(self) -> typing.Any:
        """URLs are compared by their string representation."""
        return str(self)

    def __repr__(self) -> str:
        """URL representation with password masking."""
        url_str = str(self)
        if hasattr(self, "password") and self.password:
            # Mask password in representation
            masked_url = url_str.replace(f":{self.password}@", ":********@")
            return f"{self.__class__.__name__}({masked_url!r})"
        return f"{self.__class__.__name__}({url_str!r})"


class MultiDictBase(DataStructureBase):
    """Base class for multi-dict data structures."""

    def _get_comparison_key(self) -> typing.Any:
        """Multi-dicts are compared by their sorted list representation."""
        if hasattr(self, "_list"):
            return tuple(sorted(self._list))
        elif hasattr(self, "multi_items"):
            return tuple(sorted(self.multi_items()))
        else:
            # Fallback to dict items
            return tuple(sorted(self.items()))

    def _get_repr_attrs(self) -> typing.Dict[str, typing.Any]:
        """Show the list of items in representation."""
        if hasattr(self, "multi_items"):
            items = self.multi_items()
        elif hasattr(self, "_list"):
            items = self._list
        else:
            items = list(self.items())

        return {"items": items}


class PriorityDataStructure(OrderedDataStructure, RepresentableDataStructure):
    """Base class for data structures that are ordered by priority."""

    def _get_ordering_key(self) -> typing.Any:
        """Order by priority attribute."""
        if hasattr(self, "priority"):
            return self.priority
        else:
            raise AttributeError(
                f"{self.__class__.__name__} must have a 'priority' attribute"
            )

    def _get_comparison_key(self) -> typing.Any:
        """Use hash-relevant attributes for comparison."""
        return self._get_hash_key()

    @abstractmethod
    def _get_hash_key(self) -> typing.Any:
        """Return the key used for hashing this object."""
        pass
