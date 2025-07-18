"""Integration tests for ALTER TABLE operations.

These tests verify full end-to-end ALTER TABLE functionality including
diff engine detection, SQL generation, and roundtrip fidelity.
"""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "add column to existing table",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL
            );
            """,
            """
            ALTER TABLE test_schema.users ADD COLUMN email character varying(255) NOT NULL DEFAULT 'user@example.com';
            """,
            [
                'ALTER TABLE "test_schema"."users" ADD COLUMN "email" character varying(255) NOT NULL DEFAULT \'user@example.com\'',
            ],
            [
                ("r:test_schema.users", "test_schema"),
            ],
            [
                ("r:test_schema.users", "test_schema"),
            ],
        ),
        (
            "drop column from existing table",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.products (
                id integer NOT NULL,
                name text NOT NULL,
                old_field text,
                description text
            );
            """,
            """
            ALTER TABLE test_schema.products DROP COLUMN old_field;
            """,
            [
                'ALTER TABLE "test_schema"."products" DROP COLUMN "old_field";',
            ],
            [
                ("r:test_schema.products", "test_schema"),
            ],
            [
                ("r:test_schema.products", "test_schema"),
            ],
        ),
        (
            "change column type",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.conversions (
                id integer NOT NULL,
                price numeric(8,2),
                status_code smallint
            );
            """,
            """
            ALTER TABLE test_schema.conversions ALTER COLUMN price TYPE numeric(12,4);
            """,
            [
                'ALTER TABLE "test_schema"."conversions" ALTER COLUMN "price" TYPE numeric(12,4);',
            ],
            [
                ("r:test_schema.conversions", "test_schema"),
            ],
            [
                ("r:test_schema.conversions", "test_schema"),
            ],
        ),
        (
            "set column default",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.settings (
                id integer NOT NULL,
                enabled boolean,
                created_at timestamp
            );
            """,
            """
            ALTER TABLE test_schema.settings ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
            """,
            [
                'ALTER TABLE "test_schema"."settings" ALTER COLUMN "created_at" SET DEFAULT CURRENT_TIMESTAMP;',
            ],
            [
                ("r:test_schema.settings", "test_schema"),
            ],
            [
                ("r:test_schema.settings", "test_schema"),
            ],
        ),
        (
            "drop column default",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.configs (
                id integer NOT NULL,
                status text DEFAULT 'pending',
                value text
            );
            """,
            """
            ALTER TABLE test_schema.configs ALTER COLUMN status DROP DEFAULT;
            """,
            [
                'ALTER TABLE "test_schema"."configs" ALTER COLUMN "status" DROP DEFAULT;',
            ],
            [
                ("r:test_schema.configs", "test_schema"),
            ],
            [
                ("r:test_schema.configs", "test_schema"),
            ],
        ),
        (
            "set column not null",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                name text
            );
            INSERT INTO test_schema.users (id, name) VALUES (1, 'Test User');
            """,
            """
            ALTER TABLE test_schema.users ALTER COLUMN name SET NOT NULL;
            """,
            [
                'ALTER TABLE "test_schema"."users" ALTER COLUMN "name" SET NOT NULL;',
            ],
            [
                ("r:test_schema.users", "test_schema"),
            ],
            [
                ("r:test_schema.users", "test_schema"),
            ],
        ),
        (
            "drop column not null",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.profiles (
                id integer NOT NULL,
                email text NOT NULL,
                phone text
            );
            """,
            """
            ALTER TABLE test_schema.profiles ALTER COLUMN email DROP NOT NULL;
            """,
            [
                'ALTER TABLE "test_schema"."profiles" ALTER COLUMN "email" DROP NOT NULL;',
            ],
            [
                ("r:test_schema.profiles", "test_schema"),
            ],
            [
                ("r:test_schema.profiles", "test_schema"),
            ],
        ),
        (
            "multiple alter operations - state-based diffing",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.evolution (
                id integer NOT NULL,
                old_name varchar(50),
                status text DEFAULT 'pending'
            );
            """,
            """
            ALTER TABLE test_schema.evolution ADD COLUMN email character varying(255);
            ALTER TABLE test_schema.evolution ALTER COLUMN old_name TYPE text;
            ALTER TABLE test_schema.evolution ALTER COLUMN status DROP DEFAULT;
            ALTER TABLE test_schema.evolution DROP COLUMN status;
            """,
            [
                # Note: State-based diffing correctly omits "DROP DEFAULT" for status column
                # since the column is ultimately dropped. The intermediate DEFAULT removal
                # has no impact on the final state, demonstrating correct diff behavior.
                'ALTER TABLE "test_schema"."evolution" ADD COLUMN "email" character varying(255);',
                'ALTER TABLE "test_schema"."evolution" ALTER COLUMN "old_name" TYPE text;',
                'ALTER TABLE "test_schema"."evolution" DROP COLUMN "status";',
            ],
            [
                ("r:test_schema.evolution", "test_schema"),
            ],
            [
                ("r:test_schema.evolution", "test_schema"),
            ],
        ),
        (
            "complex column changes",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.complex_changes (
                id integer NOT NULL,
                email text,
                status varchar(20) DEFAULT 'active',
                created_at timestamp
            );
            """,
            """
            ALTER TABLE test_schema.complex_changes ALTER COLUMN email TYPE character varying(255);
            ALTER TABLE test_schema.complex_changes ALTER COLUMN email SET NOT NULL;
            ALTER TABLE test_schema.complex_changes ALTER COLUMN email SET DEFAULT 'user@example.com';
            ALTER TABLE test_schema.complex_changes ALTER COLUMN status DROP DEFAULT;
            ALTER TABLE test_schema.complex_changes ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
            """,
            [
                'ALTER TABLE "test_schema"."complex_changes" ALTER COLUMN "email" TYPE character varying(255);',
                'ALTER TABLE "test_schema"."complex_changes" ALTER COLUMN "email" SET NOT NULL;',
                'ALTER TABLE "test_schema"."complex_changes" ALTER COLUMN "email" SET DEFAULT \'user@example.com\'::character varying;',
                'ALTER TABLE "test_schema"."complex_changes" ALTER COLUMN "status" DROP DEFAULT;',
                'ALTER TABLE "test_schema"."complex_changes" ALTER COLUMN "created_at" SET DEFAULT CURRENT_TIMESTAMP;',
            ],
            [
                ("r:test_schema.complex_changes", "test_schema"),
            ],
            [
                ("r:test_schema.complex_changes", "test_schema"),
            ],
        ),
        (
            "generated column operations",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id integer NOT NULL,
                first_name text NOT NULL,
                last_name text NOT NULL
            );
            """,
            """
            ALTER TABLE test_schema.users ADD COLUMN full_name text GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED;
            ALTER TABLE test_schema.users ADD COLUMN email character varying(255) DEFAULT 'user@example.com';
            """,
            [
                'ALTER TABLE "test_schema"."users" ADD COLUMN "full_name" text GENERATED ALWAYS AS ((first_name || \' \'::text) || last_name) STORED;',
                'ALTER TABLE "test_schema"."users" ADD COLUMN "email" character varying(255) DEFAULT \'user@example.com\'::character varying;',
            ],
            [
                ("r:test_schema.users", "test_schema"),
            ],
            [
                ("r:test_schema.users", "test_schema"),
            ],
        ),
        (
            "drop generated column",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.products (
                id integer NOT NULL,
                price numeric(10,2) NOT NULL,
                tax_rate numeric(5,4) DEFAULT 0.0875,
                total_price numeric(10,2) GENERATED ALWAYS AS (price * (1 + tax_rate)) STORED
            );
            """,
            """
            ALTER TABLE test_schema.products DROP COLUMN total_price;
            """,
            [
                'ALTER TABLE "test_schema"."products" DROP COLUMN "total_price";',
            ],
            [
                ("r:test_schema.products", "test_schema"),
            ],
            [
                ("r:test_schema.products", "test_schema"),
            ],
        ),
        (
            "alter generated column expression",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.calculations (
                id integer NOT NULL,
                value_a numeric NOT NULL,
                value_b numeric NOT NULL,
                computed numeric GENERATED ALWAYS AS (value_a + value_b) STORED
            );
            """,
            """
            ALTER TABLE test_schema.calculations DROP COLUMN computed;
            ALTER TABLE test_schema.calculations ADD COLUMN computed numeric GENERATED ALWAYS AS (value_a * value_b) STORED;
            """,
            [
                'ALTER TABLE "test_schema"."calculations" DROP COLUMN "computed";',
                'ALTER TABLE "test_schema"."calculations" ADD COLUMN "computed" numeric GENERATED ALWAYS AS (value_a * value_b) STORED;',
            ],
            [
                ("r:test_schema.calculations", "test_schema"),
            ],
            [
                ("r:test_schema.calculations", "test_schema"),
            ],
        ),
    ],
)
@pytest.mark.integration
def test_alter_table_operations_roundtrip(
    session,
    alt_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test end-to-end roundtrip fidelity for ALTER TABLE operations."""
    roundtrip_fidelity_test(
        master_session=session,
        branch_session=alt_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=test_name,
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_dependencies,
        expected_branch_dependencies=expected_branch_dependencies,
    )
