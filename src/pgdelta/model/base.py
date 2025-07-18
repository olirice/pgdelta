"""Base model for all PostgreSQL catalog objects."""

from abc import ABC, abstractmethod
from dataclasses import MISSING, dataclass, field, fields
from typing import Any


@dataclass(slots=True, frozen=True)
class BasePgModel(ABC):
    """Base model for all PostgreSQL catalog objects."""

    def semantic_equality(self, other: "BasePgModel") -> bool:
        """Compare objects using only identity and data fields."""
        if not isinstance(other, self.__class__):
            return False

        # Compare identity and data fields using the helper methods
        return (
            self.get_identity_fields() == other.get_identity_fields()
            and self.get_data_fields() == other.get_data_fields()
        )

    @property
    @abstractmethod
    def stable_id(self) -> str:
        """
        Database-portable stable identifier for dependency resolution.

        This identifier remains constant across database dumps/restores and
        is used for cross-database dependency resolution with NetworkX.
        """

    def get_identity_fields(self) -> dict[str, Any]:
        """Get all identity fields and their values."""
        identity_fields = {}
        for field_obj in fields(self):
            if field_obj.metadata.get("field_type") == "identity":
                identity_fields[field_obj.name] = getattr(self, field_obj.name)
        return identity_fields

    def get_data_fields(self) -> dict[str, Any]:
        """Get all data fields and their values."""
        data_fields = {}
        for field_obj in fields(self):
            if field_obj.metadata.get("field_type") == "data":
                data_fields[field_obj.name] = getattr(self, field_obj.name)
        return data_fields


def field_data(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    metadata: dict[str, Any] | None = None,
    kw_only: Any = MISSING,
    **kwargs: Any,
) -> Any:
    """Create a dataclass field marked as data type."""
    if metadata is None:
        metadata = {}
    metadata = {"field_type": "data", **metadata}

    field_kwargs = {
        "init": init,
        "repr": repr,
        "hash": hash,
        "compare": compare,
        "metadata": metadata,
        **kwargs,
    }

    if default is not MISSING:
        field_kwargs["default"] = default
    if default_factory is not MISSING:
        field_kwargs["default_factory"] = default_factory
    if kw_only is not MISSING:
        field_kwargs["kw_only"] = kw_only

    return field(**field_kwargs)


def field_identity(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    metadata: dict[str, Any] | None = None,
    kw_only: Any = MISSING,
    **kwargs: Any,
) -> Any:
    """Create a dataclass field marked as identity type."""
    if metadata is None:
        metadata = {}
    metadata = {"field_type": "identity", **metadata}

    field_kwargs = {
        "init": init,
        "repr": repr,
        "hash": hash,
        "compare": compare,
        "metadata": metadata,
        **kwargs,
    }

    if default is not MISSING:
        field_kwargs["default"] = default
    if default_factory is not MISSING:
        field_kwargs["default_factory"] = default_factory
    if kw_only is not MISSING:
        field_kwargs["kw_only"] = kw_only

    return field(**field_kwargs)


def field_internal(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    metadata: dict[str, Any] | None = None,
    kw_only: Any = MISSING,
    **kwargs: Any,
) -> Any:
    """Create a dataclass field marked as internal type."""
    if metadata is None:
        metadata = {}
    metadata = {"field_type": "internal", **metadata}

    field_kwargs = {
        "init": init,
        "repr": repr,
        "hash": hash,
        "compare": compare,
        "metadata": metadata,
        **kwargs,
    }

    if default is not MISSING:
        field_kwargs["default"] = default
    if default_factory is not MISSING:
        field_kwargs["default_factory"] = default_factory
    if kw_only is not MISSING:
        field_kwargs["kw_only"] = kw_only

    return field(**field_kwargs)


def field_ignore(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
    metadata: dict[str, Any] | None = None,
    kw_only: Any = MISSING,
    **kwargs: Any,
) -> Any:
    """Create a dataclass field marked as ignore type."""
    if metadata is None:
        metadata = {}
    metadata = {"field_type": "ignore", **metadata}

    field_kwargs = {
        "init": init,
        "repr": repr,
        "hash": hash,
        "compare": compare,
        "metadata": metadata,
        **kwargs,
    }

    if default is not MISSING:
        field_kwargs["default"] = default
    if default_factory is not MISSING:
        field_kwargs["default_factory"] = default_factory
    if kw_only is not MISSING:
        field_kwargs["kw_only"] = kw_only

    return field(**field_kwargs)
