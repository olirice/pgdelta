"""Unit tests for catalog extraction."""

from sqlalchemy import text

from pgdelta.catalog import extract_catalog


def test_extract_empty_catalog(session):
    """Test extracting from empty database."""
    catalog = extract_catalog(session)

    # PostgreSQL always has a public schema by default
    assert len(catalog.namespaces) == 1
    assert "public" in catalog.namespaces
    assert len(catalog.classes) == 0
    assert len(catalog.attributes) == 0
    assert len(catalog.depends) == 0


def test_extract_schema_only(session):
    """Test extracting catalog with only schema."""
    # Create schema inline - no shared fixtures
    session.execute(text("CREATE SCHEMA test_schema"))
    session.commit()

    catalog = extract_catalog(session)

    assert len(catalog.namespaces) == 2  # public + test_schema
    assert "test_schema" in catalog.namespaces
    assert "public" in catalog.namespaces
    assert catalog.namespaces["test_schema"].nspname == "test_schema"
    assert len(catalog.classes) == 0
    assert len(catalog.attributes) == 0


def test_extract_schema_with_table(session):
    """Test extracting catalog with schema and table."""
    # Create all data inline
    session.execute(text("CREATE SCHEMA test_schema"))
    session.execute(
        text(
            """
        CREATE TABLE test_schema.users (
            id serial PRIMARY KEY,
            name text NOT NULL,
            email text
        )
    """
        )
    )
    session.commit()

    catalog = extract_catalog(session)

    # Check schema
    assert len(catalog.namespaces) == 2  # public + test_schema
    assert "test_schema" in catalog.namespaces
    assert "public" in catalog.namespaces

    # Check table (serial creates sequence and index too)
    tables = [c for c in catalog.classes.values() if c.relkind == "r"]
    assert len(tables) == 1
    assert "r:test_schema.users" in catalog.classes
    table = catalog.classes["r:test_schema.users"]
    assert table.relname == "users"
    assert table.namespace == "test_schema"
    assert table.relkind == "r"

    # Check columns
    columns = catalog.get_class_attributes("r:test_schema.users")
    assert len(columns) == 3

    # Check column names and order
    column_names = [col.attname for col in columns]
    assert "id" in column_names
    assert "name" in column_names
    assert "email" in column_names

    # Check column details
    id_col = next(col for col in columns if col.attname == "id")
    assert id_col.formatted_type == "integer"
    assert id_col.attnotnull is True

    name_col = next(col for col in columns if col.attname == "name")
    assert name_col.formatted_type == "text"
    assert name_col.attnotnull is True

    email_col = next(col for col in columns if col.attname == "email")
    assert email_col.formatted_type == "text"
    assert email_col.attnotnull is False


def test_extract_multiple_schemas(session):
    """Test extracting multiple schemas."""
    # Create all data inline
    session.execute(text("CREATE SCHEMA schema_a"))
    session.execute(text("CREATE SCHEMA schema_b"))
    session.execute(text("CREATE TABLE schema_a.table_a (id int)"))
    session.execute(text("CREATE TABLE schema_b.table_b (id int)"))
    session.commit()

    catalog = extract_catalog(session)

    assert len(catalog.namespaces) == 3  # public + schema_a + schema_b
    assert "public" in catalog.namespaces
    assert "schema_a" in catalog.namespaces
    assert "schema_b" in catalog.namespaces

    # Check tables (filter to only count tables, not sequences/indexes)
    tables = [c for c in catalog.classes.values() if c.relkind == "r"]
    assert len(tables) == 2
    assert "r:schema_a.table_a" in catalog.classes
    assert "r:schema_b.table_b" in catalog.classes


def test_extract_table_with_various_types(session):
    """Test extracting table with various column types."""
    # Create all data inline
    session.execute(text("CREATE SCHEMA test_schema"))
    session.execute(
        text(
            """
        CREATE TABLE test_schema.type_test (
            col_int integer,
            col_bigint bigint,
            col_text text,
            col_varchar varchar(50),
            col_boolean boolean,
            col_timestamp timestamp,
            col_numeric numeric(10,2),
            col_uuid uuid
        )
    """
        )
    )
    session.commit()

    catalog = extract_catalog(session)

    columns = catalog.get_class_attributes("r:test_schema.type_test")
    assert len(columns) == 8

    # Check type names are properly resolved
    type_names = {col.attname: col.formatted_type for col in columns}
    assert type_names["col_int"] == "integer"
    assert type_names["col_bigint"] == "bigint"
    assert type_names["col_text"] == "text"
    assert type_names["col_varchar"] == "character varying(50)"
    assert type_names["col_boolean"] == "boolean"
    assert type_names["col_timestamp"] == "timestamp without time zone"
    assert type_names["col_numeric"] == "numeric(10,2)"
    assert type_names["col_uuid"] == "uuid"


def test_extract_system_schemas_filtered(session):
    """Test that system schemas are properly filtered out."""
    # Create a table in public schema (should be included)
    session.execute(text("CREATE TABLE public.test_table (id int)"))
    session.commit()

    catalog = extract_catalog(session)

    # Should only contain public schema, not system schemas
    schema_names = set(catalog.namespaces.keys())
    system_schemas = {"information_schema", "pg_catalog", "pg_toast"}

    assert not system_schemas.intersection(schema_names)
    assert "public" in schema_names


def test_extract_table_dependencies(session):
    """Test that dependencies are extracted."""
    # Create all data inline
    session.execute(text("CREATE SCHEMA test_schema"))
    session.execute(
        text(
            """
        CREATE TABLE test_schema.users (
            id serial PRIMARY KEY,
            name text
        )
    """
        )
    )
    session.commit()

    catalog = extract_catalog(session)

    # Should have some dependencies (table depends on schema, etc.)
    assert len(catalog.depends) > 0

    # Dependencies should have stable IDs (even if placeholder)
    for dep in catalog.depends:
        assert dep.dependent_stable_id is not None
        assert dep.referenced_stable_id is not None
        assert dep.deptype in ["n", "a", "i"]  # Normal, auto, internal


def test_extract_column_constraints(session):
    """Test extracting column constraints."""
    # Create all data inline
    session.execute(text("CREATE SCHEMA test_schema"))
    session.execute(
        text(
            """
        CREATE TABLE test_schema.constrained_table (
            id serial PRIMARY KEY,
            name text NOT NULL,
            email text,
            age integer CHECK (age > 0)
        )
    """
        )
    )
    session.commit()

    catalog = extract_catalog(session)

    columns = catalog.get_class_attributes("r:test_schema.constrained_table")

    # Check NOT NULL constraints
    id_col = next(col for col in columns if col.attname == "id")
    assert id_col.attnotnull is True

    name_col = next(col for col in columns if col.attname == "name")
    assert name_col.attnotnull is True

    email_col = next(col for col in columns if col.attname == "email")
    assert email_col.attnotnull is False

    age_col = next(col for col in columns if col.attname == "age")
    assert age_col.attnotnull is False


def test_extract_column_ordering(session):
    """Test that columns are extracted in correct order."""
    # Create all data inline
    session.execute(text("CREATE SCHEMA test_schema"))
    session.execute(
        text(
            """
        CREATE TABLE test_schema.ordered_table (
            third_col text,
            first_col integer,
            second_col boolean
        )
    """
        )
    )
    session.commit()

    catalog = extract_catalog(session)

    columns = catalog.get_class_attributes("r:test_schema.ordered_table")

    # Columns should be ordered by attnum (creation order)
    assert len(columns) == 3
    assert columns[0].attname == "third_col"
    assert columns[0].attnum == 1
    assert columns[1].attname == "first_col"
    assert columns[1].attnum == 2
    assert columns[2].attname == "second_col"
    assert columns[2].attnum == 3
