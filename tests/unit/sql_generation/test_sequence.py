"""Sequence SQL generation tests."""

import pytest

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.sequence import AlterSequence, CreateSequence, DropSequence
from pgdelta.model import PgSequence


def test_create_sequence_basic():
    """Test basic CREATE SEQUENCE SQL generation."""
    sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    change = CreateSequence(
        stable_id="public.test_seq",
        sequence=sequence,
    )

    sql = generate_sql(change)

    assert 'CREATE SEQUENCE "public"."test_seq"' in sql
    assert sql.endswith(";")


def test_create_sequence_with_options():
    """Test CREATE SEQUENCE with non-default options."""
    sequence = PgSequence(
        seqname="custom_seq",
        namespace="test_schema",
        data_type="integer",
        increment_by=5,
        min_value=10,
        max_value=1000,
        start_value=20,
        cache_size=50,
        cycle=True,
        oid=16385,
        owned_by_table="test_table",
        owned_by_column="id",
    )

    change = CreateSequence(
        stable_id="test_schema.custom_seq",
        sequence=sequence,
    )

    sql = generate_sql(change)

    assert 'CREATE SEQUENCE "test_schema"."custom_seq"' in sql
    assert "AS integer" in sql
    assert "INCREMENT BY 5" in sql
    assert "MINVALUE 10" in sql
    assert "MAXVALUE 1000" in sql
    assert "START WITH 20" in sql
    assert "CACHE 50" in sql
    assert "CYCLE" in sql
    # OWNED BY is handled by CREATE TABLE or ALTER SEQUENCE commands, not in CREATE SEQUENCE
    assert sql.endswith(";")


def test_create_sequence_no_min_max():
    """Test CREATE SEQUENCE with no min/max values."""
    sequence = PgSequence(
        seqname="no_limits_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=None,
        max_value=None,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16386,
        owned_by_table=None,
        owned_by_column=None,
    )

    change = CreateSequence(
        stable_id="public.no_limits_seq",
        sequence=sequence,
    )

    sql = generate_sql(change)

    assert "NO MINVALUE" in sql
    assert "NO MAXVALUE" in sql
    assert "NO CYCLE" in sql


def test_drop_sequence_basic():
    """Test basic DROP SEQUENCE SQL generation."""
    change = DropSequence(
        stable_id="public.test_seq",
        namespace="public",
        seqname="test_seq",
    )

    sql = generate_sql(change)

    assert 'DROP SEQUENCE "public"."test_seq"' in sql
    assert sql.endswith(";")


def test_alter_sequence_no_changes():
    """Test ALTER SEQUENCE with no actual changes."""
    old_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    new_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    change = AlterSequence(
        stable_id="public.test_seq",
        old_sequence=old_sequence,
        new_sequence=new_sequence,
    )

    sql = generate_sql(change)

    # Should return empty string when no changes
    assert sql == ""


def test_alter_sequence_increment_change():
    """Test ALTER SEQUENCE changing increment."""
    old_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    new_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=10,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    change = AlterSequence(
        stable_id="public.test_seq",
        old_sequence=old_sequence,
        new_sequence=new_sequence,
    )

    sql = generate_sql(change)

    assert 'ALTER SEQUENCE "public"."test_seq"' in sql
    assert "INCREMENT BY 10" in sql
    assert sql.endswith(";")


def test_alter_sequence_owned_by_change():
    """Test ALTER SEQUENCE changing owned by."""
    old_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    new_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table="test_table",
        owned_by_column="id",
    )

    change = AlterSequence(
        stable_id="public.test_seq",
        old_sequence=old_sequence,
        new_sequence=new_sequence,
    )

    sql = generate_sql(change)

    assert 'OWNED BY "public"."test_table"."id"' in sql
    assert sql.endswith(";")


def test_alter_sequence_remove_owned_by():
    """Test ALTER SEQUENCE removing owned by."""
    old_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table="test_table",
        owned_by_column="id",
    )

    new_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    change = AlterSequence(
        stable_id="public.test_seq",
        old_sequence=old_sequence,
        new_sequence=new_sequence,
    )

    sql = generate_sql(change)

    assert "OWNED BY NONE" in sql
    assert sql.endswith(";")


def test_alter_sequence_multiple_changes():
    """Test ALTER SEQUENCE with multiple property changes."""
    old_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
        oid=16384,
        owned_by_table=None,
        owned_by_column=None,
    )

    new_sequence = PgSequence(
        seqname="test_seq",
        namespace="public",
        data_type="integer",
        increment_by=5,
        min_value=10,
        max_value=1000,
        start_value=1,  # start_value change should be included
        cache_size=20,
        cycle=True,
        oid=16384,
        owned_by_table="test_table",
        owned_by_column="id",
    )

    change = AlterSequence(
        stable_id="public.test_seq",
        old_sequence=old_sequence,
        new_sequence=new_sequence,
    )

    sql = generate_sql(change)

    # Should have both the property changes and the owned by change
    assert 'ALTER SEQUENCE "public"."test_seq"' in sql
    assert "AS integer" in sql
    assert "INCREMENT BY 5" in sql
    assert "MINVALUE 10" in sql
    assert "MAXVALUE 1000" in sql
    assert "CACHE 20" in sql
    assert "CYCLE" in sql
    assert 'OWNED BY "public"."test_table"."id"' in sql
    # Should have two statements (one for properties, one for owned by)
    assert sql.count(";") == 2


@pytest.mark.parametrize(
    "sequence_name,namespace,expected_quoted",
    [
        ("simple", "public", '"public"."simple"'),
        ("with-dash", "test_schema", '"test_schema"."with-dash"'),
        ("with_underscore", "public", '"public"."with_underscore"'),
        ("with space", "public", '"public"."with space"'),
        ("WITH_CAPS", "TEST_SCHEMA", '"TEST_SCHEMA"."WITH_CAPS"'),
    ],
)
def test_sequence_name_quoting(sequence_name, namespace, expected_quoted):
    """Test that sequence names are properly quoted."""
    change = DropSequence(
        stable_id=f"{namespace}.{sequence_name}",
        namespace=namespace,
        seqname=sequence_name,
    )

    sql = generate_sql(change)
    assert expected_quoted in sql
