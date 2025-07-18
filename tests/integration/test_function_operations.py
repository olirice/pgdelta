"""Integration tests for function operations and dependencies."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "simple function creation",
            "CREATE SCHEMA test_schema",
            """
            CREATE FUNCTION test_schema.add_numbers(a integer, b integer)
            RETURNS integer
            LANGUAGE sql
            IMMUTABLE
            AS 'SELECT $1 + $2';
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.add_numbers(a integer, b integer)",
                "RETURNS integer",
                "LANGUAGE sql",
                "IMMUTABLE",
                "SELECT $1 + $2",
            ],
            [],  # Master has no dependencies (empty state)
            [
                (
                    "function:test_schema.add_numbers(a integer, b integer)",
                    "test_schema",
                ),
            ],
        ),
        (
            "plpgsql function with security definer",
            "CREATE SCHEMA test_schema",
            """
            CREATE FUNCTION test_schema.get_user_count()
            RETURNS bigint
            LANGUAGE plpgsql
            SECURITY DEFINER
            STABLE
            AS $$
            BEGIN
                RETURN (SELECT COUNT(*) FROM pg_catalog.pg_user);
            END;
            $$;
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.get_user_count()",
                "RETURNS bigint",
                "LANGUAGE plpgsql",
                "SECURITY DEFINER",
                "STABLE",
            ],
            [],
            [
                ("function:test_schema.get_user_count()", "test_schema"),
            ],
        ),
        (
            "function with complex attributes",
            "CREATE SCHEMA test_schema",
            """
            CREATE FUNCTION test_schema.expensive_function(input_data text)
            RETURNS text
            LANGUAGE plpgsql
            VOLATILE
            STRICT
            PARALLEL RESTRICTED
            COST 1000
            AS $$
            BEGIN
                -- Simulate expensive operation
                PERFORM pg_sleep(0.1);
                RETURN upper(input_data);
            END;
            $$;
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.expensive_function(input_data text)",
                "RETURNS text",
                "LANGUAGE plpgsql",
                "STRICT",
                "PARALLEL RESTRICTED",
                "COST 1000",
            ],
            [],
            [
                (
                    "function:test_schema.expensive_function(input_data text)",
                    "test_schema",
                ),
            ],
        ),
        (
            "function with configuration parameters",
            "CREATE SCHEMA test_schema",
            """
            CREATE FUNCTION test_schema.config_function()
            RETURNS void
            LANGUAGE plpgsql
            SET work_mem = '256MB'
            SET statement_timeout = '30s'
            AS $$
            BEGIN
                -- Function with custom configuration
                RAISE NOTICE 'Function executed with custom config';
            END;
            $$;
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.config_function()",
                "LANGUAGE plpgsql",
                "SET work_mem TO '256MB'",
                "SET statement_timeout TO '30s'",
            ],
            [],
            [
                ("function:test_schema.config_function()", "test_schema"),
            ],
        ),
        (
            "function replacement (alter)",
            "CREATE SCHEMA test_schema",
            """
            CREATE FUNCTION test_schema.version_function()
            RETURNS text
            LANGUAGE sql
            IMMUTABLE
            AS 'SELECT ''v1.0''';

            -- Replace the function with a new version
            CREATE OR REPLACE FUNCTION test_schema.version_function()
            RETURNS text
            LANGUAGE sql
            IMMUTABLE
            AS 'SELECT ''v2.0''';
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.version_function()",
                "RETURNS text",
                "SELECT 'v2.0'",
            ],
            [],
            [
                ("function:test_schema.version_function()", "test_schema"),
            ],
        ),
        (
            "function overloading - same name different signatures",
            "CREATE SCHEMA test_schema",
            """
            -- Function with one parameter
            CREATE FUNCTION test_schema.format_value(input_val integer)
            RETURNS text
            LANGUAGE sql
            IMMUTABLE
            AS 'SELECT input_val::text';

            -- Function with two parameters (overload)
            CREATE FUNCTION test_schema.format_value(input_val integer, prefix text)
            RETURNS text
            LANGUAGE sql
            IMMUTABLE
            AS 'SELECT prefix || input_val::text';
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.format_value(input_val integer)",
                "CREATE OR REPLACE FUNCTION test_schema.format_value(input_val integer, prefix text)",
                "RETURNS text",
                "LANGUAGE sql",
                "IMMUTABLE",
            ],
            [],
            [
                ("function:test_schema.format_value(input_val integer)", "test_schema"),
                (
                    "function:test_schema.format_value(input_val integer, prefix text)",
                    "test_schema",
                ),
            ],
        ),
        (
            "function used in table default",
            "CREATE SCHEMA test_schema",
            """
            CREATE FUNCTION test_schema.get_timestamp()
            RETURNS timestamp
            LANGUAGE sql
            STABLE
            AS 'SELECT NOW()';

            CREATE TABLE test_schema.events (
                id serial PRIMARY KEY,
                name text NOT NULL,
                created_at timestamp DEFAULT test_schema.get_timestamp()
            );
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.get_timestamp()",
                'CREATE TABLE "test_schema"."events"',
                "DEFAULT test_schema.get_timestamp()",
            ],
            [],
            [
                ("function:test_schema.get_timestamp()", "test_schema"),
                ("r:test_schema.events", "test_schema"),
                ("S:test_schema.events_id_seq", "test_schema"),
                ("S:test_schema.events_id_seq", "r:test_schema.events"),
                ("i:test_schema.events_pkey", "test_schema.events.events_pkey"),
                ("test_schema.events.events_pkey", "r:test_schema.events"),
            ],
        ),
        (
            "function no changes when identical",
            """
            CREATE SCHEMA test_schema;
            CREATE FUNCTION test_schema.stable_function()
            RETURNS integer
            LANGUAGE sql
            AS 'SELECT 42';
            """,  # Create function in both databases
            "",  # No additional changes in branch
            [],  # No changes expected - both databases have same function
            [
                ("function:test_schema.stable_function()", "test_schema"),
            ],
            [
                ("function:test_schema.stable_function()", "test_schema"),
            ],
        ),
    ],
)
@pytest.mark.integration
def test_function_operations(
    master_session,
    branch_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test function CREATE, ALTER, and DROP operations with dependency tracking."""
    roundtrip_fidelity_test(
        master_session=master_session,
        branch_session=branch_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=f"Function operation: {test_name}",
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_dependencies,
        expected_branch_dependencies=expected_branch_dependencies,
    )


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_operation_order,expected_master_deps,expected_branch_deps",
    [
        (
            "function before constraint that uses it",
            "CREATE SCHEMA test_schema",
            r"""
            CREATE FUNCTION test_schema.validate_email(email text)
            RETURNS boolean
            LANGUAGE sql
            IMMUTABLE
            AS $$
                SELECT email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
            $$;

            CREATE TABLE test_schema.users (
                id serial PRIMARY KEY,
                name text NOT NULL,
                email text,
                CONSTRAINT valid_email CHECK (test_schema.validate_email(email))
            );
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.validate_email(email text)",
                'CREATE TABLE "test_schema"."users"',
                "CHECK (test_schema.validate_email(email))",
            ],
            [
                "S:test_schema.users_id_seq",
                "function:test_schema.validate_email(email text)",
                "r:test_schema.users",
                "test_schema.users.users_pkey",
                "test_schema.users.valid_email",
            ],
            [],  # expected_master_deps
            [  # expected_branch_deps
                ("S:test_schema.users_id_seq", "test_schema"),
                ("S:test_schema.users_id_seq", "r:test_schema.users"),
                ("function:test_schema.validate_email(email text)", "test_schema"),
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("r:test_schema.users", "test_schema"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                (
                    "test_schema.users.valid_email",
                    "function:test_schema.validate_email(email text)",
                ),
                ("test_schema.users.valid_email", "r:test_schema.users"),
            ],
        ),
        (
            "function before view that uses it",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.products (
                id serial PRIMARY KEY,
                name text NOT NULL,
                price numeric(10,2)
            );

            CREATE FUNCTION test_schema.format_price(price numeric)
            RETURNS text
            LANGUAGE sql
            IMMUTABLE
            AS 'SELECT ''$'' || price::text';

            CREATE VIEW test_schema.product_display AS
            SELECT
                id,
                name,
                test_schema.format_price(price) as formatted_price
            FROM test_schema.products;
            """,
            [
                'CREATE TABLE "test_schema"."products"',
                "CREATE OR REPLACE FUNCTION test_schema.format_price(price numeric)",
                'CREATE VIEW "test_schema"."product_display"',
                "test_schema.format_price(price)",
            ],
            [
                "S:test_schema.products_id_seq",
                "function:test_schema.format_price(price numeric)",
                "r:test_schema.products",
                "v:test_schema.product_display",
                "test_schema.products.products_pkey",
            ],
            [],  # expected_master_deps
            [  # expected_branch_deps
                ("S:test_schema.products_id_seq", "r:test_schema.products"),
                ("S:test_schema.products_id_seq", "test_schema"),
                ("function:test_schema.format_price(price numeric)", "test_schema"),
                ("i:test_schema.products_pkey", "test_schema.products.products_pkey"),
                ("r:test_schema.products", "test_schema"),
                ("test_schema.products.products_pkey", "r:test_schema.products"),
                ("v:test_schema.product_display", "r:test_schema.products"),
                ("v:test_schema.product_display", "test_schema"),
            ],
        ),
    ],
)
@pytest.mark.integration
def test_function_dependency_ordering(
    master_session,
    branch_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_operation_order,
    expected_master_deps,
    expected_branch_deps,
):
    """Test that functions are created in correct dependency order."""
    roundtrip_fidelity_test(
        master_session=master_session,
        branch_session=branch_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=f"Function dependency ordering: {test_name}",
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_deps,
        expected_branch_dependencies=expected_branch_deps,
        expected_operation_order=expected_operation_order,
    )


@pytest.mark.integration
def test_function_semantic_equality(master_session, branch_session):
    """Test that functions with identical semantics are considered equal."""
    # Setup: Create a function in both databases
    initial_sql = """
    CREATE SCHEMA test_schema;
    CREATE FUNCTION test_schema.test_func(x integer)
    RETURNS integer
    LANGUAGE sql
    IMMUTABLE
    AS 'SELECT x * 2';
    """

    from sqlalchemy import text

    master_session.execute(text(initial_sql))
    branch_session.execute(text(initial_sql))

    # Test: Extract catalogs and ensure functions are equal
    from pgdelta.catalog import extract_catalog

    master_catalog = extract_catalog(master_session)
    branch_catalog = extract_catalog(branch_session)

    # Verify function exists in both catalogs
    func_stable_id = "function:test_schema.test_func(x integer)"
    assert func_stable_id in master_catalog.procedures
    assert func_stable_id in branch_catalog.procedures

    # Verify semantic equality
    master_func = master_catalog.procedures[func_stable_id]
    branch_func = branch_catalog.procedures[func_stable_id]
    assert master_func.semantic_equality(branch_func)

    # Verify no changes generated
    changes = master_catalog.diff(branch_catalog)
    assert len(changes) == 0


@pytest.mark.integration
def test_function_with_dependencies_roundtrip(master_session, branch_session):
    """Test complex function scenario with multiple dependencies."""
    roundtrip_fidelity_test(
        master_session=master_session,
        branch_session=branch_session,
        initial_setup="CREATE SCHEMA test_schema",
        test_sql="""
        -- Create a utility function first
        CREATE FUNCTION test_schema.safe_divide(numerator numeric, denominator numeric)
        RETURNS numeric
        LANGUAGE sql
        IMMUTABLE
        STRICT
        AS $$
            SELECT CASE
                WHEN denominator = 0 THEN NULL
                ELSE numerator / denominator
            END
        $$;

        -- Create tables that will use the function
        CREATE TABLE test_schema.metrics (
            id serial PRIMARY KEY,
            name text NOT NULL,
            total_value numeric DEFAULT 0,
            count_value integer DEFAULT 0
        );

        -- Create a view that uses the function
        CREATE VIEW test_schema.metric_averages AS
        SELECT
            id,
            name,
            test_schema.safe_divide(total_value, count_value::numeric) as average_value
        FROM test_schema.metrics
        WHERE count_value > 0;

        -- Create another function that depends on the first function
        CREATE FUNCTION test_schema.get_metric_summary(metric_id integer)
        RETURNS text
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            metric_name text;
            avg_val numeric;
        BEGIN
            SELECT m.name, test_schema.safe_divide(m.total_value, m.count_value::numeric)
            INTO metric_name, avg_val
            FROM test_schema.metrics m
            WHERE m.id = metric_id;

            RETURN metric_name || ': ' || COALESCE(avg_val::text, 'N/A');
        END;
        $$;
        """,
        description="Complex function scenario with multiple dependencies",
        expected_sql_terms=[
            "CREATE OR REPLACE FUNCTION test_schema.safe_divide(numerator numeric, denominator numeric)",
            'CREATE TABLE "test_schema"."metrics"',
            'CREATE VIEW "test_schema"."metric_averages"',
            "CREATE OR REPLACE FUNCTION test_schema.get_metric_summary(metric_id integer)",
            "test_schema.safe_divide(total_value, (count_value)::numeric)",
            "test_schema.safe_divide(m.total_value, m.count_value::numeric)",
        ],
        expected_master_dependencies=[],
        expected_branch_dependencies=[
            (
                "function:test_schema.safe_divide(numerator numeric, denominator numeric)",
                "test_schema",
            ),
            ("r:test_schema.metrics", "test_schema"),
            ("S:test_schema.metrics_id_seq", "test_schema"),
            ("S:test_schema.metrics_id_seq", "r:test_schema.metrics"),
            ("i:test_schema.metrics_pkey", "test_schema.metrics.metrics_pkey"),
            ("test_schema.metrics.metrics_pkey", "r:test_schema.metrics"),
            ("v:test_schema.metric_averages", "test_schema"),
            ("v:test_schema.metric_averages", "r:test_schema.metrics"),
            (
                "function:test_schema.get_metric_summary(metric_id integer)",
                "test_schema",
            ),
        ],
    )
