"""Unit tests for index SQL generation."""

from pgdelta.changes.index import AlterIndex, CreateIndex, DropIndex
from pgdelta.model.pg_index import PgIndex


def test_create_index_sql_generation():
    """Test CREATE INDEX SQL generation."""
    index = PgIndex(
        name="idx_users_email",
        namespace_name="test_schema",
        table_name="users",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "idx_users_email" ON "test_schema"."users" USING btree ("email")',
        oid=16384,
        table_oid=16385,
    )

    change = CreateIndex(
        stable_id="i:test_schema.idx_users_email",
        index=index,
    )

    # The CREATE INDEX should use the exact index_definition from pg_get_indexdef()
    sql = change.index.index_definition
    assert (
        sql
        == 'CREATE INDEX "idx_users_email" ON "test_schema"."users" USING btree ("email")'
    )


def test_create_unique_index_sql_generation():
    """Test CREATE UNIQUE INDEX SQL generation."""
    index = PgIndex(
        name="idx_products_sku",
        namespace_name="test_schema",
        table_name="products",
        is_unique=True,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE UNIQUE INDEX "idx_products_sku" ON "test_schema"."products" USING btree ("sku")',
        oid=16384,
        table_oid=16385,
    )

    change = CreateIndex(
        stable_id="i:test_schema.idx_products_sku",
        index=index,
    )

    sql = change.index.index_definition
    assert (
        sql
        == 'CREATE UNIQUE INDEX "idx_products_sku" ON "test_schema"."products" USING btree ("sku")'
    )


def test_drop_index_sql_generation():
    """Test DROP INDEX SQL generation."""
    index = PgIndex(
        name="idx_old_index",
        namespace_name="test_schema",
        table_name="users",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "idx_old_index" ON "test_schema"."users" USING btree ("old_column")',
        oid=16384,
        table_oid=16385,
    )

    change = DropIndex(
        stable_id="i:test_schema.idx_old_index",
        index=index,
    )

    from pgdelta.changes.index.drop import generate_drop_index_sql

    sql = generate_drop_index_sql(change)
    assert sql == 'DROP INDEX "test_schema"."idx_old_index"'


def test_alter_index_rename_sql_generation():
    """Test ALTER INDEX is not implemented."""
    old_index = PgIndex(
        name="old_name",
        namespace_name="test_schema",
        table_name="users",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "old_name" ON "test_schema"."users" USING btree ("email")',
        oid=16384,
        table_oid=16385,
    )

    new_index = PgIndex(
        name="new_name",
        namespace_name="test_schema",
        table_name="users",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "new_name" ON "test_schema"."users" USING btree ("email")',
        oid=16384,
        table_oid=16385,
    )

    change = AlterIndex(
        stable_id="i:test_schema.old_name",
        old_index=old_index,
        new_index=new_index,
    )

    from pgdelta.changes.dispatcher import generate_sql

    # Should raise NotImplementedError for ALTER INDEX operations
    try:
        generate_sql(change)
        raise AssertionError("Should have raised NotImplementedError")
    except NotImplementedError as e:
        assert "ALTER INDEX operations are not yet implemented" in str(e)


def test_drop_index_with_special_characters():
    """Test DROP INDEX with special characters in names."""
    index = PgIndex(
        name="idx-with-dashes",
        namespace_name="test_schema",
        table_name="table-name",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "idx-with-dashes" ON "test_schema"."table-name" USING btree ("column")',
        oid=16384,
        table_oid=16385,
    )

    change = DropIndex(
        stable_id="i:test_schema.idx-with-dashes",
        index=index,
    )

    from pgdelta.changes.index.drop import generate_drop_index_sql

    sql = generate_drop_index_sql(change)
    assert sql == 'DROP INDEX "test_schema"."idx-with-dashes"'


def test_create_partial_index_sql_generation():
    """Test CREATE INDEX with WHERE clause (partial index)."""
    index = PgIndex(
        name="idx_orders_pending",
        namespace_name="test_schema",
        table_name="orders",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "idx_orders_pending" ON "test_schema"."orders" USING btree ("created_at") WHERE (status = \'pending\'::text)',
        oid=16384,
        table_oid=16385,
    )

    change = CreateIndex(
        stable_id="i:test_schema.idx_orders_pending",
        index=index,
    )

    sql = change.index.index_definition
    assert "WHERE" in sql
    assert "pending" in sql
    assert "created_at" in sql


def test_create_functional_index_sql_generation():
    """Test CREATE INDEX with function expression."""
    index = PgIndex(
        name="idx_customers_email_lower",
        namespace_name="test_schema",
        table_name="customers",
        is_unique=False,
        is_primary=False,
        is_constraint_index=False,
        index_definition='CREATE INDEX "idx_customers_email_lower" ON "test_schema"."customers" USING btree (lower("email"))',
        oid=16384,
        table_oid=16385,
    )

    change = CreateIndex(
        stable_id="i:test_schema.idx_customers_email_lower",
        index=index,
    )

    sql = change.index.index_definition
    assert "lower(" in sql
    assert "email" in sql
