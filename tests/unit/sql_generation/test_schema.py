"""Schema SQL generation tests."""

import pytest

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.schema import CreateSchema, DropSchema


def test_create_schema_basic():
    """Test basic CREATE SCHEMA SQL generation."""
    change = CreateSchema(
        stable_id="test_schema",
        nspname="test_schema",
    )

    sql = generate_sql(change)

    assert 'CREATE SCHEMA "test_schema"' in sql
    assert sql.endswith(";")


def test_create_schema_with_quotes():
    """Test CREATE SCHEMA with special characters."""
    change = CreateSchema(
        stable_id="test-schema",
        nspname="test-schema",
    )

    sql = generate_sql(change)

    assert 'CREATE SCHEMA "test-schema"' in sql
    assert sql.endswith(";")


def test_drop_schema_basic():
    """Test basic DROP SCHEMA SQL generation."""
    change = DropSchema(
        stable_id="test_schema",
        nspname="test_schema",
    )

    sql = generate_sql(change)

    assert 'DROP SCHEMA "test_schema"' in sql
    assert sql.endswith(";")


# CASCADE functionality intentionally removed - dependency resolution handles ordering


@pytest.mark.parametrize(
    "schema_name,expected_quoted",
    [
        ("simple", '"simple"'),
        ("with-dash", '"with-dash"'),
        ("with_underscore", '"with_underscore"'),
        ("with space", '"with space"'),
        ("WITH_CAPS", '"WITH_CAPS"'),
    ],
)
def test_schema_name_quoting(schema_name, expected_quoted):
    """Test that schema names are properly quoted."""
    change = CreateSchema(
        stable_id=schema_name,
        nspname=schema_name,
    )

    sql = generate_sql(change)
    assert expected_quoted in sql
