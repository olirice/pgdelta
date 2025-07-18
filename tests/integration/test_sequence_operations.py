"""Integration tests for sequence operations."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.parametrize(
    "description,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "create basic sequence",
            "CREATE SCHEMA test_schema;",
            "CREATE SEQUENCE test_schema.test_seq;",
            ["CREATE SEQUENCE", "test_schema", "test_seq"],
            [],  # Master has no dependencies (empty state)
            [("S:test_schema.test_seq", "test_schema")],  # Sequence depends on schema
        ),
        (
            "create sequence with options",
            "CREATE SCHEMA test_schema;",
            """
            CREATE SEQUENCE test_schema.custom_seq
                AS integer
                INCREMENT BY 2
                MINVALUE 10
                MAXVALUE 1000
                START WITH 10
                CACHE 5
                CYCLE;
            """,
            [
                "CREATE SEQUENCE",
                "test_schema",
                "custom_seq",
                "AS integer",
                "INCREMENT BY 2",
                "MINVALUE 10",
                "MAXVALUE 1000",
                "CACHE 5",
                "CYCLE",
            ],
            [],  # Master has no dependencies (empty state)
            [("S:test_schema.custom_seq", "test_schema")],  # Sequence depends on schema
        ),
        (
            "drop sequence",
            """
            CREATE SCHEMA test_schema;
            CREATE SEQUENCE test_schema.test_seq;
            """,  # Both databases get schema + sequence
            "DROP SEQUENCE test_schema.test_seq;",  # Branch drops the sequence
            ["DROP SEQUENCE", "test_schema", "test_seq"],
            [
                ("S:test_schema.test_seq", "test_schema")
            ],  # Dependency exists in master catalog
            [],  # Branch has no dependencies (sequence dropped)
        ),
        (
            "create table with serial column (sequence dependency)",
            "CREATE SCHEMA test_schema;",
            """
            CREATE TABLE test_schema.users (
                id SERIAL PRIMARY KEY,
                name TEXT
            );
            """,
            ["CREATE SEQUENCE", "CREATE TABLE", "users_id_seq", "users"],
            [],  # Master has no dependencies (empty state)
            # Serial column creates multiple dependencies:
            [
                (
                    "S:test_schema.users_id_seq",
                    "r:test_schema.users",
                ),  # sequence owned by table
                (
                    "S:test_schema.users_id_seq",
                    "test_schema",
                ),  # sequence depends on schema
                (
                    "i:test_schema.users_pkey",
                    "test_schema.users.users_pkey",
                ),  # index depends on constraint
                ("r:test_schema.users", "test_schema"),  # table depends on schema
                (
                    "test_schema.users.users_pkey",
                    "r:test_schema.users",
                ),  # constraint depends on table
            ],
        ),
        (
            "alter sequence properties",
            """
            CREATE SCHEMA test_schema;
            CREATE SEQUENCE test_schema.test_seq INCREMENT BY 1 CACHE 1;
            """,
            """
            ALTER SEQUENCE test_schema.test_seq INCREMENT BY 5 CACHE 10;
            """,
            ["ALTER SEQUENCE", "INCREMENT BY 5", "CACHE 10"],
            [("S:test_schema.test_seq", "test_schema")],  # Sequence depends on schema
            [("S:test_schema.test_seq", "test_schema")],  # Sequence depends on schema
        ),
    ],
)
def test_sequence_operations(
    session,
    alt_session,
    initial_setup,
    test_sql,
    description,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test sequence operations roundtrip fidelity."""
    roundtrip_fidelity_test(
        master_session=session,
        branch_session=alt_session,
        initial_setup=initial_setup,
        test_sql=test_sql,
        description=description,
        expected_sql_terms=expected_terms,
        expected_master_dependencies=expected_master_dependencies,
        expected_branch_dependencies=expected_branch_dependencies,
    )
