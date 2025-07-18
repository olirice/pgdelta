"""Integration tests for table operations."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "simple table with columns",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.users (
                id integer,
                name text NOT NULL,
                email text
            )
            """,
            [
                'CREATE TABLE "test_schema"."users"',
                '"id" integer',
                '"name" text NOT NULL',
                '"email" text',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.users", "test_schema"),
            ],
        ),
        (
            "table with constraints",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.constrained_table (
                id integer,
                name text NOT NULL,
                email text,
                age integer
            )
            """,
            [
                'CREATE TABLE "test_schema"."constrained_table"',
                '"id" integer',
                '"name" text NOT NULL',
                '"email" text',
                '"age" integer',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.constrained_table", "test_schema"),
            ],
        ),
        (
            "multiple tables",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.users (
                id integer,
                name text NOT NULL
            );

            CREATE TABLE test_schema.posts (
                id integer,
                title text NOT NULL,
                content text
            );
            """,
            [
                'CREATE TABLE "test_schema"."users"',
                'CREATE TABLE "test_schema"."posts"',
                '"id" integer',
                '"name" text NOT NULL',
                '"title" text NOT NULL',
                '"content" text',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.users", "test_schema"),
                ("r:test_schema.posts", "test_schema"),
            ],
        ),
        (
            "table with various types",
            "CREATE SCHEMA test_schema",
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
            """,
            [
                'CREATE TABLE "test_schema"."type_test"',
                '"col_int" integer',
                '"col_bigint" bigint',
                '"col_text" text',
                '"col_varchar" character varying(50)',
                '"col_boolean" boolean',
                '"col_timestamp" timestamp without time zone',
                '"col_numeric" numeric(10,2)',
                '"col_uuid" uuid',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.type_test", "test_schema"),
            ],
        ),
        (
            "table in public schema",
            None,
            """
            CREATE TABLE public.simple_table (
                id integer,
                name text
            )
            """,
            [
                'CREATE TABLE "public"."simple_table"',
                '"id" integer',
                '"name" text',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:public.simple_table", "public"),
            ],
        ),
        (
            "empty table",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.empty_table ()
            """,
            [
                'CREATE TABLE "test_schema"."empty_table"',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:test_schema.empty_table", "test_schema"),
            ],
        ),
        (
            "tables in multiple schemas",
            """
            CREATE SCHEMA schema_a;
            CREATE SCHEMA schema_b;
            """,
            """
            CREATE TABLE schema_a.table_a (
                id integer,
                name text
            );

            CREATE TABLE schema_b.table_b (
                id integer,
                description text
            );
            """,
            [
                'CREATE TABLE "schema_a"."table_a"',
                'CREATE TABLE "schema_b"."table_b"',
                '"id" integer',
                '"name" text',
                '"description" text',
            ],
            [],  # Master has no dependencies (empty state)
            [
                ("r:schema_a.table_a", "schema_a"),
                ("r:schema_b.table_b", "schema_b"),
            ],
        ),
    ],
)
def test_table_operations_roundtrip(
    session,
    alt_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test end-to-end roundtrip fidelity for table operations."""
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
