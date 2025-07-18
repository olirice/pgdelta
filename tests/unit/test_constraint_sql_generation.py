"""Unit tests for constraint SQL generation."""

import pytest

from pgdelta.changes.constraint import (
    AlterConstraint,
    CreateConstraint,
    DropConstraint,
    generate_alter_constraint_sql,
    generate_create_constraint_sql,
    generate_drop_constraint_sql,
)
from pgdelta.model.pg_attribute import PgAttribute
from pgdelta.model.pg_constraint import PgConstraint


def _create_test_columns() -> list[PgAttribute]:
    """Create test table columns for users table."""
    return [
        PgAttribute(
            owner_namespace="public",
            owner_name="users",
            owner_relkind="r",
            attname="id",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=54321,
            default_value=None,
            attgenerated="",
            generated_expression=None,
        ),
        PgAttribute(
            owner_namespace="public",
            owner_name="users",
            owner_relkind="r",
            attname="email",
            attnum=2,
            attnotnull=True,
            formatted_type="character varying(255)",
            attrelid=54321,
            default_value=None,
            attgenerated="",
            generated_expression=None,
        ),
    ]


def _create_orders_table_columns() -> list[PgAttribute]:
    """Create test table columns for orders table."""
    return [
        PgAttribute(
            owner_namespace="public",
            owner_name="orders",
            owner_relkind="r",
            attname="id",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=54322,
            default_value=None,
            attgenerated="",
            generated_expression=None,
        ),
        PgAttribute(
            owner_namespace="public",
            owner_name="orders",
            owner_relkind="r",
            attname="user_id",
            attnum=2,
            attnotnull=True,
            formatted_type="integer",
            attrelid=54322,
            default_value=None,
            attgenerated="",
            generated_expression=None,
        ),
    ]


def _create_referenced_table_columns() -> list[PgAttribute]:
    """Create test table columns for referenced users table."""
    return [
        PgAttribute(
            owner_namespace="public",
            owner_name="users",
            owner_relkind="r",
            attname="id",
            attnum=1,
            attnotnull=True,
            formatted_type="integer",
            attrelid=54321,
            default_value=None,
            attgenerated="",
            generated_expression=None,
        ),
    ]


def test_generate_create_primary_key_constraint_sql():
    """Test CREATE PRIMARY KEY constraint SQL generation."""
    constraint = PgConstraint(
        oid=12345,
        conname="users_pkey",
        connamespace=2200,
        conrelid=54321,
        contype="p",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=98765,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1, 2],  # Column numbers 1 and 2
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="users",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.users.users_pkey",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_create_constraint_sql(change)
    expected = 'ALTER TABLE "public"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id", "email");'

    assert sql == expected


def test_generate_create_unique_constraint_sql():
    """Test CREATE UNIQUE constraint SQL generation."""
    constraint = PgConstraint(
        oid=12346,
        conname="users_email_key",
        connamespace=2200,
        conrelid=54321,
        contype="u",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=98766,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],  # Column number 2 (email)
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="users",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.users.users_email_key",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_create_constraint_sql(change)
    expected = 'ALTER TABLE "public"."users" ADD CONSTRAINT "users_email_key" UNIQUE ("email");'

    assert sql == expected


def test_generate_create_check_constraint_sql():
    """Test CREATE CHECK constraint SQL generation."""
    constraint = PgConstraint(
        oid=12347,
        conname="users_age_check",
        connamespace=2200,
        conrelid=54321,
        contype="c",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[4],  # Column number 4
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin="(age >= 0)",
        conpredicate=None,
        namespace_name="public",
        table_name="users",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.users.users_age_check",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_create_constraint_sql(change)
    expected = 'ALTER TABLE "public"."users" ADD CONSTRAINT "users_age_check" CHECK ((age >= 0));'

    assert sql == expected


def test_generate_create_foreign_key_constraint_sql():
    """Test CREATE FOREIGN KEY constraint SQL generation."""
    constraint = PgConstraint(
        oid=12348,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,  # References users table
        confupdtype="c",  # CASCADE
        confdeltype="r",  # RESTRICT
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],  # Column number 2 (user_id)
        confkey=[1],  # References column number 1 in foreign table
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    table_columns = _create_orders_table_columns()
    referenced_table_columns = _create_referenced_table_columns()

    change = CreateConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        constraint=constraint,
        table_columns=table_columns,
        referenced_table_columns=referenced_table_columns,
    )

    sql = generate_create_constraint_sql(change)
    expected = 'ALTER TABLE "public"."orders" ADD CONSTRAINT "orders_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("id") ON UPDATE CASCADE ON DELETE RESTRICT;'

    assert sql == expected


def test_generate_create_exclusion_constraint_sql():
    """Test CREATE EXCLUSION constraint SQL generation."""
    constraint = PgConstraint(
        oid=12349,
        conname="reservations_time_excl",
        connamespace=2200,
        conrelid=54323,
        contype="x",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=98767,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1, 2],  # Columns involved in exclusion
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[2970, 2975],  # Exclusion operators
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="reservations",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.reservations.reservations_time_excl",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_create_constraint_sql(change)
    # Note: This will be a placeholder until exclusion constraint parsing is implemented
    expected = 'ALTER TABLE "public"."reservations" ADD CONSTRAINT "reservations_time_excl" EXCLUDE (<exclusion_definition_for_reservations_time_excl>);'

    assert sql == expected


def test_generate_drop_constraint_sql():
    """Test DROP constraint SQL generation."""
    constraint = PgConstraint(
        oid=12345,
        conname="users_pkey",
        connamespace=2200,
        conrelid=54321,
        contype="p",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=98765,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1],
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="users",
    )

    table_columns = _create_test_columns()

    change = DropConstraint(
        stable_id="public.users.users_pkey",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_drop_constraint_sql(change)
    expected = 'ALTER TABLE "public"."users" DROP CONSTRAINT "users_pkey";'

    assert sql == expected


def test_generate_constraint_sql_with_special_characters():
    """Test constraint SQL generation with special characters in names."""
    constraint = PgConstraint(
        oid=12350,
        conname="my-table_check$constraint",
        connamespace=2200,
        conrelid=54324,
        contype="c",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1],
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin="(value > 0)",
        conpredicate=None,
        namespace_name="my-schema",
        table_name="my-table",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="my-schema.my-table.my-table_check$constraint",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_create_constraint_sql(change)
    expected = 'ALTER TABLE "my-schema"."my-table" ADD CONSTRAINT "my-table_check$constraint" CHECK ((value > 0));'

    assert sql == expected


def test_generate_constraint_sql_unsupported_type():
    """Test constraint SQL generation with unsupported constraint type."""
    constraint = PgConstraint(
        oid=12351,
        conname="trigger_constraint",
        connamespace=2200,
        conrelid=54325,
        contype="t",  # Trigger constraint (unsupported)
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[],
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="test_table",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.test_table.trigger_constraint",
        constraint=constraint,
        table_columns=table_columns,
    )

    with pytest.raises(ValueError, match="Unsupported constraint type: t"):
        generate_create_constraint_sql(change)


def test_generate_check_constraint_missing_expression():
    """Test CHECK constraint generation with missing expression."""
    constraint = PgConstraint(
        oid=12352,
        conname="invalid_check",
        connamespace=2200,
        conrelid=54326,
        contype="c",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1],
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,  # Missing CHECK expression
        conpredicate=None,
        namespace_name="public",
        table_name="test_table",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.test_table.invalid_check",
        constraint=constraint,
        table_columns=table_columns,
    )

    with pytest.raises(
        ValueError, match="CHECK constraint invalid_check missing expression"
    ):
        generate_create_constraint_sql(change)


def test_generate_create_partial_unique_constraint_sql():
    """Test CREATE UNIQUE constraint with WHERE clause SQL generation."""
    constraint = PgConstraint(
        oid=12353,
        conname="users_email_key",
        connamespace=2200,
        conrelid=54321,
        contype="u",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=98766,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],  # Column number 2 (email)
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,
        conpredicate="is_active = true",  # WHERE clause
        namespace_name="public",
        table_name="users",
    )

    table_columns = _create_test_columns()

    change = CreateConstraint(
        stable_id="public.users.users_email_key",
        constraint=constraint,
        table_columns=table_columns,
    )

    sql = generate_create_constraint_sql(change)
    expected = 'ALTER TABLE "public"."users" ADD CONSTRAINT "users_email_key" UNIQUE ("email") WHERE (is_active = true);'

    assert sql == expected


def test_generate_alter_constraint_deferrability_sql():
    """Test ALTER CONSTRAINT deferrability SQL generation."""
    old_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,  # Not deferrable
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,  # References users table
        confupdtype="c",  # CASCADE
        confdeltype="r",  # RESTRICT
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],  # Column number 2 (user_id)
        confkey=[1],  # References column number 1 in foreign table
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    new_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=True,  # Now deferrable
        condeferred=True,  # Initially deferred
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,  # References users table
        confupdtype="c",  # CASCADE
        confdeltype="r",  # RESTRICT
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],  # Column number 2 (user_id)
        confkey=[1],  # References column number 1 in foreign table
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    table_columns = _create_orders_table_columns()
    referenced_table_columns = _create_referenced_table_columns()

    change = AlterConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        table_columns=table_columns,
        referenced_table_columns=referenced_table_columns,
    )

    sql = generate_alter_constraint_sql(change)
    expected = 'ALTER TABLE "public"."orders" ALTER CONSTRAINT "orders_user_id_fkey" DEFERRABLE INITIALLY DEFERRED;'

    assert sql == expected


def test_generate_alter_constraint_not_foreign_key_error():
    """Test ALTER CONSTRAINT error for non-foreign key constraints."""
    old_constraint = PgConstraint(
        oid=12355,
        conname="users_pkey",
        connamespace=2200,
        conrelid=54321,
        contype="p",  # Primary key, not foreign key
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=98765,
        conparentid=0,
        confrelid=0,
        confupdtype="a",
        confdeltype="a",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[1],
        confkey=[],
        conpfeqop=[],
        conppeqop=[],
        conffeqop=[],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="users",
    )

    new_constraint = old_constraint  # Same constraint

    table_columns = _create_test_columns()

    change = AlterConstraint(
        stable_id="public.users.users_pkey",
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        table_columns=table_columns,
    )

    with pytest.raises(
        ValueError,
        match="ALTER CONSTRAINT only supported for foreign key constraints, got p",
    ):
        generate_alter_constraint_sql(change)


@pytest.mark.parametrize(
    "constraint_type,expected_sql_fragment",
    [
        ("p", "PRIMARY KEY"),
        ("u", "UNIQUE"),
        ("c", "CHECK"),
        ("f", "FOREIGN KEY"),
    ],
)
def test_constraint_type_sql_generation(constraint_type, expected_sql_fragment):
    """Test SQL generation for different constraint types."""
    if constraint_type == "c":
        # CHECK constraint needs expression
        constraint = PgConstraint(
            oid=12345,
            conname="test_constraint",
            connamespace=2200,
            conrelid=54321,
            contype=constraint_type,
            condeferrable=False,
            condeferred=False,
            convalidated=True,
            contypid=0,
            conindid=0,
            conparentid=0,
            confrelid=0,
            confupdtype="a",
            confdeltype="a",
            confmatchtype="s",
            conislocal=True,
            coninhcount=0,
            connoinherit=False,
            conkey=[1],
            confkey=[],
            conpfeqop=[],
            conppeqop=[],
            conffeqop=[],
            conexclop=[],
            conbin="(value > 0)",
            conpredicate=None,
            namespace_name="public",
            table_name="test_table",
        )
    elif constraint_type == "f":
        # FOREIGN KEY constraint needs referenced table info
        constraint = PgConstraint(
            oid=12345,
            conname="test_constraint",
            connamespace=2200,
            conrelid=54321,
            contype=constraint_type,
            condeferrable=False,
            condeferred=False,
            convalidated=True,
            contypid=0,
            conindid=0,
            conparentid=0,
            confrelid=54322,  # References another table
            confupdtype="a",
            confdeltype="a",
            confmatchtype="s",
            conislocal=True,
            coninhcount=0,
            connoinherit=False,
            conkey=[1],
            confkey=[1],
            conpfeqop=[96],
            conppeqop=[96],
            conffeqop=[96],
            conexclop=[],
            conbin=None,
            conpredicate=None,
            namespace_name="public",
            table_name="test_table",
        )
    else:
        # PRIMARY KEY and UNIQUE constraints
        constraint = PgConstraint(
            oid=12345,
            conname="test_constraint",
            connamespace=2200,
            conrelid=54321,
            contype=constraint_type,
            condeferrable=False,
            condeferred=False,
            convalidated=True,
            contypid=0,
            conindid=0,
            conparentid=0,
            confrelid=0,
            confupdtype="a",
            confdeltype="a",
            confmatchtype="s",
            conislocal=True,
            coninhcount=0,
            connoinherit=False,
            conkey=[1],
            confkey=[],
            conpfeqop=[],
            conppeqop=[],
            conffeqop=[],
            conexclop=[],
            conbin=None,
            conpredicate=None,
            namespace_name="public",
            table_name="test_table",
        )

    table_columns = _create_test_columns()
    referenced_table_columns = (
        _create_referenced_table_columns() if constraint_type == "f" else None
    )

    change = CreateConstraint(
        stable_id="public.test_table.test_constraint",
        constraint=constraint,
        table_columns=table_columns,
        referenced_table_columns=referenced_table_columns,
    )

    sql = generate_create_constraint_sql(change)
    assert expected_sql_fragment in sql


def test_generate_alter_constraint_not_deferrable_sql():
    """Test ALTER CONSTRAINT changing from deferrable to not deferrable."""
    old_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=True,  # Originally deferrable
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    new_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,  # Now not deferrable
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    change = AlterConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        table_columns=_create_orders_table_columns(),
        referenced_table_columns=_create_referenced_table_columns(),
    )

    sql = generate_alter_constraint_sql(change)
    expected = 'ALTER TABLE "public"."orders" ALTER CONSTRAINT "orders_user_id_fkey" NOT DEFERRABLE;'
    assert sql == expected


def test_generate_alter_constraint_initially_immediate_sql():
    """Test ALTER CONSTRAINT changing to initially immediate."""
    old_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=True,
        condeferred=True,  # Originally deferred
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    new_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=True,
        condeferred=False,  # Now immediate
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    change = AlterConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        table_columns=_create_orders_table_columns(),
        referenced_table_columns=_create_referenced_table_columns(),
    )

    sql = generate_alter_constraint_sql(change)
    expected = 'ALTER TABLE "public"."orders" ALTER CONSTRAINT "orders_user_id_fkey" INITIALLY IMMEDIATE;'
    assert sql == expected


def test_generate_alter_constraint_no_changes_error():
    """Test ALTER CONSTRAINT error when no changes are detected."""
    # Create identical constraints
    old_constraint = PgConstraint(
        oid=12354,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    new_constraint = old_constraint  # Identical constraint

    change = AlterConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        old_constraint=old_constraint,
        new_constraint=new_constraint,
        table_columns=_create_orders_table_columns(),
        referenced_table_columns=_create_referenced_table_columns(),
    )

    with pytest.raises(
        ValueError, match="No changes detected for constraint orders_user_id_fkey"
    ):
        generate_alter_constraint_sql(change)


def test_generate_create_foreign_key_constraint_no_referenced_columns_error():
    """Test CREATE FOREIGN KEY constraint error when referenced table columns are missing."""
    constraint = PgConstraint(
        oid=12348,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    change = CreateConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        constraint=constraint,
        table_columns=_create_orders_table_columns(),
        referenced_table_columns=None,  # Missing referenced columns
    )

    with pytest.raises(
        ValueError,
        match="Foreign key constraint orders_user_id_fkey missing referenced table column information",
    ):
        generate_create_constraint_sql(change)


def test_generate_create_foreign_key_constraint_empty_referenced_columns_error():
    """Test CREATE FOREIGN KEY constraint error when referenced table columns list is empty."""
    constraint = PgConstraint(
        oid=12348,
        conname="orders_user_id_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    change = CreateConstraint(
        stable_id="public.orders.orders_user_id_fkey",
        constraint=constraint,
        table_columns=_create_orders_table_columns(),
        referenced_table_columns=[],  # Empty referenced columns list
    )

    with pytest.raises(
        ValueError,
        match="Foreign key constraint orders_user_id_fkey missing referenced table column information",
    ):
        generate_create_constraint_sql(change)


def test_get_column_names_from_key_invalid_column_number():
    """Test _get_column_names_from_key with invalid column number."""
    from pgdelta.changes.constraint.create import _get_column_names_from_key

    table_columns = _create_test_columns()  # Only has columns 1 and 2
    conkey = [1, 5]  # Column 5 doesn't exist

    with pytest.raises(ValueError, match="Column number 5 not found in table columns"):
        _get_column_names_from_key(conkey, table_columns)


def test_create_constraint_line_103_unreachable():
    """Demonstrate that line 103 in constraint/create.py is unreachable.

    This test shows that line 103 cannot be reached due to the duplicate
    check at line 96 and 102 with no modifications to referenced_table_columns
    in between.
    """
    from pgdelta.changes.constraint.create import _build_constraint_definition

    constraint = PgConstraint(
        oid=12348,
        conname="test_fkey",
        connamespace=2200,
        conrelid=54322,
        contype="f",
        condeferrable=False,
        condeferred=False,
        convalidated=True,
        contypid=0,
        conindid=0,
        conparentid=0,
        confrelid=54321,
        confupdtype="c",
        confdeltype="r",
        confmatchtype="s",
        conislocal=True,
        coninhcount=0,
        connoinherit=False,
        conkey=[2],
        confkey=[1],
        conpfeqop=[96],
        conppeqop=[96],
        conffeqop=[96],
        conexclop=[],
        conbin=None,
        conpredicate=None,
        namespace_name="public",
        table_name="orders",
    )

    table_columns = _create_orders_table_columns()

    # This should trigger the first check (line 96-99) not the second (line 102-105)
    with pytest.raises(ValueError, match="missing referenced table column information"):
        _build_constraint_definition(constraint, table_columns, None)
