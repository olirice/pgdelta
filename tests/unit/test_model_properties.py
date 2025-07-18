"""Unit tests for model property methods."""

from pgdelta.model import PgAttribute


def test_pg_attribute_stable_id():
    """Test stable_id generation for attributes."""
    attr = PgAttribute(
        owner_namespace="test_schema",
        owner_name="users",
        owner_relkind="r",
        attname="id",
        attnum=1,
        attnotnull=True,
        formatted_type="integer",
        attrelid=16384,
    )

    # stable_id format is "namespace.table.column"
    assert attr.stable_id == "test_schema.users.id"
