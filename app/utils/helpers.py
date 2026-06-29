"""General-purpose utility functions.

These helpers are used across the application for serialisation,
model-to-dict conversion, and other cross-cutting concerns.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class _OMSJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles OMS-specific types.

    Supports ``Decimal``, ``datetime``, ``date``, and ``Enum``
    instances in addition to all standard JSON types.
    """

    def default(self, o: Any) -> Any:  # noqa: D401
        """Return a serialisable representation of *o*.

        Args:
            o: The object to serialise.

        Returns:
            A JSON-compatible primitive.
        """
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


def model_to_dict(
    model: Any,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """Convert a SQLAlchemy model instance to a plain dictionary.

    Iterates over the mapper's column attributes, skipping any keys
    listed in *exclude*.  Relationship attributes are **not** included
    (use Pydantic schemas for nested serialisation).

    Args:
        model: A SQLAlchemy ORM model instance.
        exclude: Optional set of column names to omit.

    Returns:
        A dictionary mapping column names to their current values.
    """
    if model is None:
        return {}

    exclude = exclude or set()

    # ``__table__.columns`` gives us only the mapped columns, which is
    # what we want for audit logging (no relationships, no hybrids).
    result: dict[str, Any] = {}
    for column in model.__table__.columns:
        if column.key not in exclude:
            result[column.key] = getattr(model, column.key, None)
    return result


def serialize_for_audit(obj: Any) -> str | None:
    """Serialise an object to a JSON string suitable for audit storage.

    Handles ``None``, plain ``dict`` objects, and SQLAlchemy model
    instances (which are first converted via ``model_to_dict``).

    Args:
        obj: The object to serialise.  Accepts ``None``, a ``dict``,
            or a SQLAlchemy model instance.

    Returns:
        A JSON string, or ``None`` if the input is ``None``.
    """
    if obj is None:
        return None

    if isinstance(obj, dict):
        return json.dumps(obj, cls=_OMSJSONEncoder, sort_keys=True)

    # Assume SQLAlchemy model – convert to dict first.
    try:
        data = model_to_dict(obj)
    except AttributeError:
        # Last resort: try the object's own __dict__ minus SQLAlchemy
        # internal state.
        data = {
            k: v
            for k, v in vars(obj).items()
            if not k.startswith("_")
        }

    return json.dumps(data, cls=_OMSJSONEncoder, sort_keys=True)
