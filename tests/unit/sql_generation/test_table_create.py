"""CREATE TABLE SQL generation tests."""

import pytest

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.table import CreateTable
from pgdelta.model import PgAttribute


def test_create_table_basic():
    """Test basic CREATE TABLE SQL generation."""
    columns = [
        PgAttribute(
            attname="id",
            owner_namespace="test_schema",
            owner_name="users",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=16384,
            owner_relkind="r",
        ),
        PgAttribute(
            attname="name",
            owner_namespace="test_schema",
            owner_name="users",
            attnum=2,
            attnotnull=False,
            formatted_type="text",
            attrelid=16384,
            owner_relkind="r",
        ),
    ]

    change = CreateTable(
        stable_id="r:test_schema.users",
        namespace="test_schema",
        relname="users",
        columns=columns,
    )

    sql = generate_sql(change)

    assert 'CREATE TABLE "test_schema"."users"' in sql
    assert '"id" integer NOT NULL' in sql
    assert '"name" text' in sql
    assert "NOT NULL" not in sql.split('"name" text')[1].split(",")[0]


def test_create_table_empty_columns():
    """Test CREATE TABLE with no columns."""
    change = CreateTable(
        stable_id="r:test_schema.empty_table",
        namespace="test_schema",
        relname="empty_table",
        columns=[],
    )

    sql = generate_sql(change)

    assert 'CREATE TABLE "test_schema"."empty_table"' in sql
    assert sql.endswith(");")


def test_create_table_with_default_values():
    """Test CREATE TABLE with columns that have default values."""
    columns = [
        PgAttribute(
            attname="id",
            owner_namespace="public",
            owner_name="users",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=16384,
            owner_relkind="r",
            default_value="nextval('users_id_seq'::regclass)",
        ),
        PgAttribute(
            attname="created_at",
            owner_namespace="public",
            owner_name="users",
            attnum=2,
            attnotnull=False,
            formatted_type="timestamp without time zone",
            attrelid=16384,
            owner_relkind="r",
            default_value="now()",
        ),
        PgAttribute(
            attname="is_active",
            owner_namespace="public",
            owner_name="users",
            attnum=3,
            attnotnull=False,
            formatted_type="boolean",
            attrelid=16384,
            owner_relkind="r",
            default_value="true",
        ),
    ]

    change = CreateTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        columns=columns,
    )

    sql = generate_sql(change)

    assert "DEFAULT nextval('users_id_seq'::regclass)" in sql
    assert "DEFAULT now()" in sql
    assert "DEFAULT true" in sql


def test_create_table_with_inheritance():
    """Test CREATE TABLE with INHERITS clause."""
    columns = [
        PgAttribute(
            attname="id",
            owner_namespace="public",
            owner_name="admin_users",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=16384,
            owner_relkind="r",
        ),
        PgAttribute(
            attname="admin_level",
            owner_namespace="public",
            owner_name="admin_users",
            attnum=2,
            attnotnull=False,
            formatted_type="integer",
            attrelid=16384,
            owner_relkind="r",
        ),
    ]

    change = CreateTable(
        stable_id="r:public.admin_users",
        namespace="public",
        relname="admin_users",
        columns=columns,
        inherits_from=["users"],
    )

    sql = generate_sql(change)

    assert 'INHERITS ("users")' in sql


def test_create_table_with_options():
    """Test CREATE TABLE with storage options."""
    columns = [
        PgAttribute(
            attname="id",
            owner_namespace="public",
            owner_name="test_table",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=16384,
            owner_relkind="r",
        ),
    ]

    change = CreateTable(
        stable_id="r:public.test_table",
        namespace="public",
        relname="test_table",
        columns=columns,
        table_options={"fillfactor": 70, "autovacuum_enabled": False},
    )

    sql = generate_sql(change)

    assert "WITH (" in sql
    assert "fillfactor=70" in sql
    assert "autovacuum_enabled=false" in sql


def test_create_table_with_all_features():
    """Test CREATE TABLE with all supported features."""
    columns = [
        PgAttribute(
            attname="id",
            owner_namespace="public",
            owner_name="complete_table",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=16384,
            owner_relkind="r",
            default_value="nextval('seq'::regclass)",
        ),
        PgAttribute(
            attname="data",
            owner_namespace="public",
            owner_name="complete_table",
            attnum=2,
            attnotnull=False,
            formatted_type="text",
            attrelid=16384,
            owner_relkind="r",
        ),
    ]

    change = CreateTable(
        stable_id="r:public.complete_table",
        namespace="public",
        relname="complete_table",
        columns=columns,
        inherits_from=["base_table"],
        table_options={"fillfactor": 80},
    )

    sql = generate_sql(change)

    # Check all features are present
    assert "\"id\" integer DEFAULT nextval('seq'::regclass) NOT NULL" in sql
    assert '"data" text' in sql
    assert 'INHERITS ("base_table")' in sql
    assert "WITH (fillfactor=80)" in sql


@pytest.mark.parametrize(
    "table_name,expected_quoted",
    [
        ("users", '"users"'),
        ("user-profiles", '"user-profiles"'),
        ("user_profiles", '"user_profiles"'),
        ("User Profiles", '"User Profiles"'),
        ("USERS", '"USERS"'),
    ],
)
def test_table_name_quoting(table_name, expected_quoted):
    """Test that table names are properly quoted."""
    change = CreateTable(
        stable_id=f"r:test_schema.{table_name}",
        namespace="test_schema",
        relname=table_name,
        columns=[],
    )

    sql = generate_sql(change)
    assert expected_quoted in sql


def test_create_table_with_generated_columns():
    """Test CREATE TABLE with generated columns."""
    columns = [
        PgAttribute(
            attname="first_name",
            owner_namespace="public",
            owner_name="users",
            attnum=1,
            attnotnull=True,
            formatted_type="text",
            attrelid=16384,
            owner_relkind="r",
        ),
        PgAttribute(
            attname="last_name",
            owner_namespace="public",
            owner_name="users",
            attnum=2,
            attnotnull=True,
            formatted_type="text",
            attrelid=16384,
            owner_relkind="r",
        ),
        PgAttribute(
            attname="full_name",
            owner_namespace="public",
            owner_name="users",
            attnum=3,
            attnotnull=False,
            formatted_type="text",
            attrelid=16384,
            owner_relkind="r",
            attgenerated="s",
            generated_expression="first_name || ' ' || last_name",
        ),
        PgAttribute(
            attname="email",
            owner_namespace="public",
            owner_name="users",
            attnum=4,
            attnotnull=True,
            formatted_type="text",
            attrelid=16384,
            owner_relkind="r",
            default_value="'user@example.com'",
        ),
    ]

    change = CreateTable(
        stable_id="r:public.users",
        namespace="public",
        relname="users",
        columns=columns,
    )

    sql = generate_sql(change)

    # Check regular columns
    assert '"first_name" text NOT NULL' in sql
    assert '"last_name" text NOT NULL' in sql

    # Check generated column syntax
    assert (
        "\"full_name\" text GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED"
        in sql
    )

    # Check column with default value (DEFAULT comes before NOT NULL)
    assert "\"email\" text DEFAULT 'user@example.com' NOT NULL" in sql

    # Ensure generated column doesn't have DEFAULT
    full_name_part = sql.split(
        "\"full_name\" text GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED"
    )[1].split(",")[0]
    assert "DEFAULT" not in full_name_part


def test_create_table_mixed_generated_and_regular():
    """Test CREATE TABLE with mix of generated and regular columns."""
    columns = [
        PgAttribute(
            attname="price",
            owner_namespace="public",
            owner_name="products",
            attnum=1,
            attnotnull=True,
            formatted_type="numeric(10,2)",
            attrelid=16384,
            owner_relkind="r",
        ),
        PgAttribute(
            attname="tax_rate",
            owner_namespace="public",
            owner_name="products",
            attnum=2,
            attnotnull=True,
            formatted_type="numeric(5,4)",
            attrelid=16384,
            owner_relkind="r",
            default_value="0.0875",
        ),
        PgAttribute(
            attname="total_price",
            owner_namespace="public",
            owner_name="products",
            attnum=3,
            attnotnull=True,
            formatted_type="numeric(10,2)",
            attrelid=16384,
            owner_relkind="r",
            attgenerated="s",
            generated_expression="price * (1 + tax_rate)",
        ),
    ]

    change = CreateTable(
        stable_id="r:public.products",
        namespace="public",
        relname="products",
        columns=columns,
    )

    sql = generate_sql(change)

    # Check that regular columns work normally
    assert '"price" numeric(10,2) NOT NULL' in sql
    assert '"tax_rate" numeric(5,4) DEFAULT 0.0875 NOT NULL' in sql

    # Check generated column with NOT NULL
    assert (
        '"total_price" numeric(10,2) GENERATED ALWAYS AS (price * (1 + tax_rate)) STORED NOT NULL'
        in sql
    )
