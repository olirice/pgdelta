"""Integration tests for trigger operations and dependencies."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "simple trigger creation",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id serial PRIMARY KEY,
                name text NOT NULL,
                updated_at timestamp DEFAULT now()
            );
            CREATE FUNCTION test_schema.update_timestamp()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$;
            """,
            """
            CREATE TRIGGER update_timestamp_trigger
            BEFORE UPDATE ON test_schema.users
            FOR EACH ROW
            EXECUTE FUNCTION test_schema.update_timestamp();
            """,
            [
                "CREATE TRIGGER update_timestamp_trigger",
                "BEFORE UPDATE ON test_schema.users",
                "EXECUTE FUNCTION test_schema.update_timestamp()",
            ],
            [
                ("function:test_schema.update_timestamp()", "test_schema"),
                ("r:test_schema.users", "test_schema"),
                ("S:test_schema.users_id_seq", "test_schema"),
                ("S:test_schema.users_id_seq", "r:test_schema.users"),
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
            ],
            [
                ("function:test_schema.update_timestamp()", "test_schema"),
                ("r:test_schema.users", "test_schema"),
                ("S:test_schema.users_id_seq", "test_schema"),
                ("S:test_schema.users_id_seq", "r:test_schema.users"),
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                (
                    "trigger:test_schema.users.update_timestamp_trigger",
                    "function:test_schema.update_timestamp()",
                ),
                (
                    "trigger:test_schema.users.update_timestamp_trigger",
                    "r:test_schema.users",
                ),
            ],
        ),
        (
            "multi-event trigger",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.audit_log (
                id serial PRIMARY KEY,
                table_name text,
                operation text,
                old_data jsonb,
                new_data jsonb,
                changed_at timestamp DEFAULT now()
            );
            CREATE TABLE test_schema.sensitive_data (
                id serial PRIMARY KEY,
                secret_value text
            );
            CREATE FUNCTION test_schema.audit_changes()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    INSERT INTO test_schema.audit_log (table_name, operation, old_data)
                    VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD));
                    RETURN OLD;
                ELSE
                    INSERT INTO test_schema.audit_log (table_name, operation, new_data)
                    VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW));
                    RETURN NEW;
                END IF;
            END;
            $$;
            """,
            """
            CREATE TRIGGER audit_trigger
            AFTER INSERT OR UPDATE OR DELETE ON test_schema.sensitive_data
            FOR EACH ROW
            EXECUTE FUNCTION test_schema.audit_changes();
            """,
            [
                "CREATE TRIGGER audit_trigger",
                "AFTER INSERT OR DELETE OR UPDATE ON test_schema.sensitive_data",
                "EXECUTE FUNCTION test_schema.audit_changes()",
            ],
            [
                ("function:test_schema.audit_changes()", "test_schema"),
                ("r:test_schema.audit_log", "test_schema"),
                ("r:test_schema.sensitive_data", "test_schema"),
                ("S:test_schema.audit_log_id_seq", "test_schema"),
                ("S:test_schema.audit_log_id_seq", "r:test_schema.audit_log"),
                ("S:test_schema.sensitive_data_id_seq", "test_schema"),
                ("S:test_schema.sensitive_data_id_seq", "r:test_schema.sensitive_data"),
                (
                    "i:test_schema.audit_log_pkey",
                    "test_schema.audit_log.audit_log_pkey",
                ),
                ("test_schema.audit_log.audit_log_pkey", "r:test_schema.audit_log"),
                (
                    "i:test_schema.sensitive_data_pkey",
                    "test_schema.sensitive_data.sensitive_data_pkey",
                ),
                (
                    "test_schema.sensitive_data.sensitive_data_pkey",
                    "r:test_schema.sensitive_data",
                ),
            ],
            [
                ("function:test_schema.audit_changes()", "test_schema"),
                ("r:test_schema.audit_log", "test_schema"),
                ("r:test_schema.sensitive_data", "test_schema"),
                ("S:test_schema.audit_log_id_seq", "test_schema"),
                ("S:test_schema.audit_log_id_seq", "r:test_schema.audit_log"),
                ("S:test_schema.sensitive_data_id_seq", "test_schema"),
                ("S:test_schema.sensitive_data_id_seq", "r:test_schema.sensitive_data"),
                (
                    "i:test_schema.audit_log_pkey",
                    "test_schema.audit_log.audit_log_pkey",
                ),
                ("test_schema.audit_log.audit_log_pkey", "r:test_schema.audit_log"),
                (
                    "i:test_schema.sensitive_data_pkey",
                    "test_schema.sensitive_data.sensitive_data_pkey",
                ),
                (
                    "test_schema.sensitive_data.sensitive_data_pkey",
                    "r:test_schema.sensitive_data",
                ),
                (
                    "trigger:test_schema.sensitive_data.audit_trigger",
                    "function:test_schema.audit_changes()",
                ),
                (
                    "trigger:test_schema.sensitive_data.audit_trigger",
                    "r:test_schema.sensitive_data",
                ),
            ],
        ),
        (
            "conditional trigger with WHEN clause",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.products (
                id serial PRIMARY KEY,
                name text NOT NULL,
                price numeric(10,2),
                category text
            );
            CREATE FUNCTION test_schema.log_price_changes()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE NOTICE 'Price changed for product %: % -> %', NEW.name, OLD.price, NEW.price;
                RETURN NEW;
            END;
            $$;
            """,
            """
            CREATE TRIGGER price_change_trigger
            AFTER UPDATE ON test_schema.products
            FOR EACH ROW
            WHEN (OLD.price IS DISTINCT FROM NEW.price)
            EXECUTE FUNCTION test_schema.log_price_changes();
            """,
            [
                "CREATE TRIGGER price_change_trigger",
                "AFTER UPDATE ON test_schema.products",
                "WHEN ((old.price IS DISTINCT FROM new.price))",
                "EXECUTE FUNCTION test_schema.log_price_changes()",
            ],
            [
                ("function:test_schema.log_price_changes()", "test_schema"),
                ("r:test_schema.products", "test_schema"),
                ("S:test_schema.products_id_seq", "test_schema"),
                ("S:test_schema.products_id_seq", "r:test_schema.products"),
                ("i:test_schema.products_pkey", "test_schema.products.products_pkey"),
                ("test_schema.products.products_pkey", "r:test_schema.products"),
            ],
            [
                ("function:test_schema.log_price_changes()", "test_schema"),
                ("r:test_schema.products", "test_schema"),
                ("S:test_schema.products_id_seq", "test_schema"),
                ("S:test_schema.products_id_seq", "r:test_schema.products"),
                ("i:test_schema.products_pkey", "test_schema.products.products_pkey"),
                ("test_schema.products.products_pkey", "r:test_schema.products"),
                (
                    "trigger:test_schema.products.price_change_trigger",
                    "function:test_schema.log_price_changes()",
                ),
                (
                    "trigger:test_schema.products.price_change_trigger",
                    "r:test_schema.products",
                ),
            ],
        ),
        (
            "trigger dropping",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.test_table (
                id serial PRIMARY KEY,
                value text
            );
            CREATE FUNCTION test_schema.test_trigger_func()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN RETURN NEW; END;';
            CREATE TRIGGER old_trigger
            BEFORE INSERT ON test_schema.test_table
            FOR EACH ROW
            EXECUTE FUNCTION test_schema.test_trigger_func();
            """,
            "DROP TRIGGER old_trigger ON test_schema.test_table;",  # Drop trigger in branch
            [
                'DROP TRIGGER "old_trigger" ON "test_schema"."test_table"',
            ],
            [
                ("function:test_schema.test_trigger_func()", "test_schema"),
                ("r:test_schema.test_table", "test_schema"),
                ("S:test_schema.test_table_id_seq", "test_schema"),
                ("S:test_schema.test_table_id_seq", "r:test_schema.test_table"),
                (
                    "i:test_schema.test_table_pkey",
                    "test_schema.test_table.test_table_pkey",
                ),
                ("test_schema.test_table.test_table_pkey", "r:test_schema.test_table"),
                (
                    "trigger:test_schema.test_table.old_trigger",
                    "function:test_schema.test_trigger_func()",
                ),
                (
                    "trigger:test_schema.test_table.old_trigger",
                    "r:test_schema.test_table",
                ),
            ],
            [
                ("function:test_schema.test_trigger_func()", "test_schema"),
                ("r:test_schema.test_table", "test_schema"),
                ("S:test_schema.test_table_id_seq", "test_schema"),
                ("S:test_schema.test_table_id_seq", "r:test_schema.test_table"),
                (
                    "i:test_schema.test_table_pkey",
                    "test_schema.test_table.test_table_pkey",
                ),
                ("test_schema.test_table.test_table_pkey", "r:test_schema.test_table"),
            ],
        ),
        (
            "trigger replacement (modification)",
            """
            CREATE SCHEMA test_schema;
            CREATE TABLE test_schema.users (
                id serial PRIMARY KEY,
                email text UNIQUE,
                created_at timestamp DEFAULT now()
            );
            CREATE FUNCTION test_schema.validate_email()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$' THEN
                    RAISE EXCEPTION 'Invalid email format';
                END IF;
                RETURN NEW;
            END;
            $$;
            CREATE TRIGGER email_validation_trigger
            BEFORE INSERT ON test_schema.users
            FOR EACH ROW
            EXECUTE FUNCTION test_schema.validate_email();
            """,
            """
            CREATE OR REPLACE FUNCTION test_schema.validate_email()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                -- Updated validation logic
                IF NEW.email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$' THEN
                    RAISE EXCEPTION 'Invalid email format: %', NEW.email;
                END IF;
                -- Additional validation
                IF length(NEW.email) > 255 THEN
                    RAISE EXCEPTION 'Email too long';
                END IF;
                RETURN NEW;
            END;
            $$;

            -- Recreate trigger with updated timing
            DROP TRIGGER email_validation_trigger ON test_schema.users;
            CREATE TRIGGER email_validation_trigger
            BEFORE INSERT OR UPDATE ON test_schema.users
            FOR EACH ROW
            EXECUTE FUNCTION test_schema.validate_email();
            """,
            [
                "CREATE OR REPLACE FUNCTION test_schema.validate_email()",
                'DROP TRIGGER "email_validation_trigger" ON "test_schema"."users"',
                "CREATE TRIGGER email_validation_trigger",
                "BEFORE INSERT OR UPDATE ON test_schema.users",
            ],
            [
                ("function:test_schema.validate_email()", "test_schema"),
                ("r:test_schema.users", "test_schema"),
                ("S:test_schema.users_id_seq", "test_schema"),
                ("S:test_schema.users_id_seq", "r:test_schema.users"),
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("i:test_schema.users_email_key", "test_schema.users.users_email_key"),
                ("test_schema.users.users_email_key", "r:test_schema.users"),
                (
                    "trigger:test_schema.users.email_validation_trigger",
                    "function:test_schema.validate_email()",
                ),
                (
                    "trigger:test_schema.users.email_validation_trigger",
                    "r:test_schema.users",
                ),
            ],
            [
                ("function:test_schema.validate_email()", "test_schema"),
                ("r:test_schema.users", "test_schema"),
                ("S:test_schema.users_id_seq", "test_schema"),
                ("S:test_schema.users_id_seq", "r:test_schema.users"),
                ("i:test_schema.users_pkey", "test_schema.users.users_pkey"),
                ("test_schema.users.users_pkey", "r:test_schema.users"),
                ("i:test_schema.users_email_key", "test_schema.users.users_email_key"),
                ("test_schema.users.users_email_key", "r:test_schema.users"),
                (
                    "trigger:test_schema.users.email_validation_trigger",
                    "function:test_schema.validate_email()",
                ),
                (
                    "trigger:test_schema.users.email_validation_trigger",
                    "r:test_schema.users",
                ),
            ],
        ),
    ],
)
@pytest.mark.integration
def test_trigger_operations(
    master_session,
    branch_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test trigger CREATE, DROP, and modification operations with dependency tracking."""
    roundtrip_fidelity_test(
        master_session=master_session,
        branch_session=branch_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=f"Trigger operation: {test_name}",
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_dependencies,
        expected_branch_dependencies=expected_branch_dependencies,
    )


@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_operation_order,expected_master_deps,expected_branch_deps",
    [
        (
            "trigger after function dependency",
            "CREATE SCHEMA test_schema",
            """
            CREATE TABLE test_schema.events (
                id serial PRIMARY KEY,
                event_type text,
                occurred_at timestamp DEFAULT now()
            );

            CREATE FUNCTION test_schema.notify_event()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                PERFORM pg_notify('event_occurred', NEW.event_type);
                RETURN NEW;
            END;
            $$;

            CREATE TRIGGER event_notification_trigger
            AFTER INSERT ON test_schema.events
            FOR EACH ROW
            EXECUTE FUNCTION test_schema.notify_event();
            """,
            [
                'CREATE TABLE "test_schema"."events"',
                "CREATE OR REPLACE FUNCTION test_schema.notify_event()",
                "CREATE TRIGGER event_notification_trigger",
                "EXECUTE FUNCTION test_schema.notify_event()",
            ],
            [
                "S:test_schema.events_id_seq",
                "function:test_schema.notify_event()",
                "r:test_schema.events",
                "test_schema.events.events_pkey",
                "trigger:test_schema.events.event_notification_trigger",
            ],
            [],  # expected_master_deps
            [  # expected_branch_deps
                ("S:test_schema.events_id_seq", "test_schema"),
                ("S:test_schema.events_id_seq", "r:test_schema.events"),
                ("function:test_schema.notify_event()", "test_schema"),
                ("i:test_schema.events_pkey", "test_schema.events.events_pkey"),
                ("r:test_schema.events", "test_schema"),
                ("test_schema.events.events_pkey", "r:test_schema.events"),
                (
                    "trigger:test_schema.events.event_notification_trigger",
                    "function:test_schema.notify_event()",
                ),
                (
                    "trigger:test_schema.events.event_notification_trigger",
                    "r:test_schema.events",
                ),
            ],
        ),
    ],
)
@pytest.mark.integration
def test_trigger_dependency_ordering(
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
    """Test that triggers are created in correct dependency order."""
    roundtrip_fidelity_test(
        master_session=master_session,
        branch_session=branch_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=f"Trigger dependency ordering: {test_name}",
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_deps,
        expected_branch_dependencies=expected_branch_deps,
        expected_operation_order=expected_operation_order,
    )


@pytest.mark.integration
def test_trigger_semantic_equality(master_session, branch_session):
    """Test that triggers with identical semantics are considered equal."""
    # Setup: Create a trigger in both databases
    initial_sql = """
    CREATE SCHEMA test_schema;
    CREATE TABLE test_schema.test_table (
        id serial PRIMARY KEY,
        value text
    );
    CREATE FUNCTION test_schema.test_func()
    RETURNS trigger
    LANGUAGE plpgsql
    AS 'BEGIN RETURN NEW; END;';
    CREATE TRIGGER test_trigger
    BEFORE INSERT ON test_schema.test_table
    FOR EACH ROW
    EXECUTE FUNCTION test_schema.test_func();
    """

    from sqlalchemy import text

    master_session.execute(text(initial_sql))
    branch_session.execute(text(initial_sql))

    # Test: Extract catalogs and ensure triggers are equal
    from pgdelta.catalog import extract_catalog

    master_catalog = extract_catalog(master_session)
    branch_catalog = extract_catalog(branch_session)

    # Verify trigger exists in both catalogs
    trigger_stable_id = "trigger:test_schema.test_table.test_trigger"
    assert trigger_stable_id in master_catalog.triggers
    assert trigger_stable_id in branch_catalog.triggers

    # Verify semantic equality
    master_trigger = master_catalog.triggers[trigger_stable_id]
    branch_trigger = branch_catalog.triggers[trigger_stable_id]
    assert master_trigger.semantic_equality(branch_trigger)

    # Verify no changes generated
    changes = master_catalog.diff(branch_catalog)
    assert len(changes) == 0


@pytest.mark.integration
def test_trigger_with_dependencies_roundtrip(master_session, branch_session):
    """Test complex trigger scenario with multiple dependencies."""
    roundtrip_fidelity_test(
        master_session=master_session,
        branch_session=branch_session,
        initial_setup="CREATE SCHEMA test_schema",
        test_sql="""
        -- Create base table
        CREATE TABLE test_schema.orders (
            id serial PRIMARY KEY,
            customer_id integer NOT NULL,
            total_amount numeric(10,2),
            status text DEFAULT 'pending',
            created_at timestamp DEFAULT now(),
            updated_at timestamp DEFAULT now()
        );

        -- Create audit table
        CREATE TABLE test_schema.order_audit (
            id serial PRIMARY KEY,
            order_id integer,
            old_status text,
            new_status text,
            changed_at timestamp DEFAULT now()
        );

        -- Create trigger function for status changes
        CREATE FUNCTION test_schema.audit_order_status()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                INSERT INTO test_schema.order_audit (order_id, old_status, new_status)
                VALUES (NEW.id, OLD.status, NEW.status);
            END IF;
            RETURN NEW;
        END;
        $$;

        -- Create trigger function for timestamp updates
        CREATE FUNCTION test_schema.update_order_timestamp()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;

        -- Create triggers
        CREATE TRIGGER order_status_audit_trigger
        AFTER UPDATE ON test_schema.orders
        FOR EACH ROW
        WHEN (OLD.status IS DISTINCT FROM NEW.status)
        EXECUTE FUNCTION test_schema.audit_order_status();

        CREATE TRIGGER order_timestamp_trigger
        BEFORE UPDATE ON test_schema.orders
        FOR EACH ROW
        EXECUTE FUNCTION test_schema.update_order_timestamp();
        """,
        description="Complex trigger scenario with multiple dependencies",
        expected_sql_terms=[
            'CREATE TABLE "test_schema"."orders"',
            'CREATE TABLE "test_schema"."order_audit"',
            "CREATE OR REPLACE FUNCTION test_schema.audit_order_status()",
            "CREATE OR REPLACE FUNCTION test_schema.update_order_timestamp()",
            "CREATE TRIGGER order_status_audit_trigger",
            "CREATE TRIGGER order_timestamp_trigger",
            "WHEN ((old.status IS DISTINCT FROM new.status))",
        ],
        expected_master_dependencies=[],
        expected_branch_dependencies=[
            ("S:test_schema.orders_id_seq", "test_schema"),
            ("S:test_schema.orders_id_seq", "r:test_schema.orders"),
            ("S:test_schema.order_audit_id_seq", "test_schema"),
            ("S:test_schema.order_audit_id_seq", "r:test_schema.order_audit"),
            ("function:test_schema.audit_order_status()", "test_schema"),
            ("function:test_schema.update_order_timestamp()", "test_schema"),
            ("i:test_schema.orders_pkey", "test_schema.orders.orders_pkey"),
            ("test_schema.orders.orders_pkey", "r:test_schema.orders"),
            (
                "i:test_schema.order_audit_pkey",
                "test_schema.order_audit.order_audit_pkey",
            ),
            ("test_schema.order_audit.order_audit_pkey", "r:test_schema.order_audit"),
            ("r:test_schema.orders", "test_schema"),
            ("r:test_schema.order_audit", "test_schema"),
            (
                "trigger:test_schema.orders.order_status_audit_trigger",
                "function:test_schema.audit_order_status()",
            ),
            (
                "trigger:test_schema.orders.order_status_audit_trigger",
                "r:test_schema.orders",
            ),
            (
                "trigger:test_schema.orders.order_timestamp_trigger",
                "function:test_schema.update_order_timestamp()",
            ),
            (
                "trigger:test_schema.orders.order_timestamp_trigger",
                "r:test_schema.orders",
            ),
        ],
    )
