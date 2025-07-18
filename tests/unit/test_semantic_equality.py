"""Unit tests for semantic equality in PgCatalog."""

from pgdelta.catalog import catalog
from pgdelta.model import PgAttribute, PgClass, PgNamespace, PgSequence


def test_empty_catalogs_are_equal():
    """Test that two empty catalogs are semantically equal."""
    catalog1 = catalog()
    catalog2 = catalog()
    assert catalog1.semantically_equals(catalog2)


def test_catalogs_with_same_schema_are_equal():
    """Test that catalogs with the same schema are semantically equal."""
    schema = PgNamespace(
        oid=16385,
        nspname="test_schema",
    )

    catalog1 = catalog(
        namespaces=[schema],
    )
    catalog2 = catalog(
        namespaces=[schema],
    )
    assert catalog1.semantically_equals(catalog2)


def test_catalogs_with_different_schema_count_are_not_equal():
    """Test that catalogs with different schema counts are not equal."""
    schema = PgNamespace(
        oid=16385,
        nspname="test_schema",
    )

    catalog1 = catalog(
        namespaces=[schema],
    )
    catalog2 = catalog()
    assert not catalog1.semantically_equals(catalog2)


def test_catalogs_with_same_tables_are_equal():
    """Test that catalogs with the same tables are semantically equal."""
    class_obj = PgClass(
        oid=16384,
        relname="users",
        relkind="r",  # table
        namespace="test_schema",
    )

    catalog1 = catalog(
        classes=[class_obj],
    )
    catalog2 = catalog(
        classes=[class_obj],
    )
    assert catalog1.semantically_equals(catalog2)


def test_catalogs_with_sequences_are_properly_compared():
    """Test that catalogs with sequences are compared properly."""
    class_obj = PgClass(
        oid=16384,
        relname="users",
        relkind="r",  # table
        namespace="test_schema",
    )

    sequence_obj = PgSequence(
        oid=16387,
        seqname="users_id_seq",
        namespace="test_schema",
        data_type="bigint",
        increment_by=1,
        min_value=1,
        max_value=9223372036854775807,
        start_value=1,
        cache_size=1,
        cycle=False,
    )

    # Catalog with table only
    catalog1 = catalog(
        classes=[class_obj],
    )

    # Catalog with table and sequence
    catalog2 = catalog(
        classes=[class_obj],
        sequences=[sequence_obj],
    )

    # Should NOT be equal because sequences are now properly compared
    assert not catalog1.semantically_equals(catalog2)

    # Two catalogs with same sequences should be equal
    catalog3 = catalog(
        classes=[class_obj],
        sequences=[sequence_obj],
    )
    assert catalog2.semantically_equals(catalog3)


def test_catalogs_with_same_columns_are_equal():
    """Test that catalogs with the same columns are semantically equal."""
    column = PgAttribute(
        owner_namespace="test_schema",
        owner_name="users",
        owner_relkind="r",
        attname="id",
        attnum=1,
        attnotnull=True,
        formatted_type="integer",
        attrelid=16384,
    )

    catalog1 = catalog(
        attributes=[column],
    )
    catalog2 = catalog(
        attributes=[column],
    )
    assert catalog1.semantically_equals(catalog2)


def test_catalogs_with_different_columns_are_not_equal():
    """Test that catalogs with different columns are not equal."""
    # Create a table to go with the columns
    class_obj = PgClass(
        oid=16384,
        relname="users",
        relkind="r",  # table
        namespace="test_schema",
    )

    column1 = PgAttribute(
        owner_namespace="test_schema",
        owner_name="users",
        owner_relkind="r",
        attname="id",
        attnum=1,
        attnotnull=True,
        formatted_type="integer",
        attrelid=16384,
    )

    column2 = PgAttribute(
        owner_namespace="test_schema",
        owner_name="users",
        owner_relkind="r",
        attname="name",
        attnum=2,
        attnotnull=False,
        formatted_type="text",
        attrelid=16384,
    )

    catalog1 = catalog(
        classes=[class_obj],
        attributes=[column1],
    )
    catalog2 = catalog(
        classes=[class_obj],
        attributes=[column2],
    )
    assert not catalog1.semantically_equals(catalog2)


def test_catalogs_with_different_table_count_are_not_equal():
    """Test that catalogs with different table counts are not equal."""
    class1 = PgClass(
        oid=16384,
        relname="users",
        relkind="r",  # table
        namespace="test_schema",
    )

    class2 = PgClass(
        oid=16385,
        relname="posts",
        relkind="r",  # table
        namespace="test_schema",
    )

    catalog1 = catalog(
        classes=[class1],
    )
    catalog2 = catalog(
        classes=[class1, class2],
    )
    assert not catalog1.semantically_equals(catalog2)


def test_catalogs_with_different_table_names_are_not_equal():
    """Test that catalogs with different table names are not equal."""
    class1 = PgClass(
        oid=16384,
        relname="users",
        relkind="r",  # table
        namespace="test_schema",
    )

    class2 = PgClass(
        oid=16385,
        relname="posts",
        relkind="r",  # table
        namespace="test_schema",
    )

    catalog1 = catalog(
        classes=[class1],
    )
    catalog2 = catalog(
        classes=[class2],
    )
    assert not catalog1.semantically_equals(catalog2)


def test_catalogs_with_different_column_count_are_not_equal():
    """Test that catalogs with different column counts for same table are not equal."""
    # Create a table to go with the columns
    class_obj = PgClass(
        oid=16384,
        relname="users",
        relkind="r",  # table
        namespace="test_schema",
    )

    column1 = PgAttribute(
        owner_namespace="test_schema",
        owner_name="users",
        owner_relkind="r",
        attname="id",
        attnum=1,
        attnotnull=True,
        formatted_type="integer",
        attrelid=16384,
    )

    column2 = PgAttribute(
        owner_namespace="test_schema",
        owner_name="users",
        owner_relkind="r",
        attname="name",
        attnum=2,
        attnotnull=False,
        formatted_type="text",
        attrelid=16384,
    )

    catalog1 = catalog(
        classes=[class_obj],
        attributes=[column1],
    )
    catalog2 = catalog(
        classes=[class_obj],
        attributes=[column1, column2],
    )
    assert not catalog1.semantically_equals(catalog2)
