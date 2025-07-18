"""Integration tests for policy dependency tracking."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.integration
@pytest.mark.roundtrip
@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "policy depends on table",
            """
            CREATE SCHEMA security;
            CREATE TABLE security.users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT UNIQUE
            );
            """,
            """
            ALTER TABLE security.users ENABLE ROW LEVEL SECURITY;
            CREATE POLICY user_isolation ON security.users
                FOR ALL
                TO public
                USING (true);
            """,
            [
                "ALTER TABLE",
                "ENABLE ROW LEVEL SECURITY",
                "CREATE POLICY",
                "user_isolation",
                '"security"."users"',
                "FOR ALL",
                "TO public",
                "USING",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:security.users", "security"),  # Table depends on schema
                (
                    "security.users.users_pkey",
                    "r:security.users",
                ),  # Primary key depends on table
                (
                    "i:security.users_pkey",
                    "security.users.users_pkey",
                ),  # Index depends on constraint
                (
                    "security.users.users_email_key",
                    "r:security.users",
                ),  # Unique constraint depends on table
                (
                    "i:security.users_email_key",
                    "security.users.users_email_key",
                ),  # Unique index depends on constraint
            ],
            # Branch dependencies (after enabling RLS and creating policy)
            [
                ("r:security.users", "security"),  # Table depends on schema
                (
                    "security.users.users_pkey",
                    "r:security.users",
                ),  # Primary key depends on table
                (
                    "i:security.users_pkey",
                    "security.users.users_pkey",
                ),  # Index depends on constraint
                (
                    "security.users.users_email_key",
                    "r:security.users",
                ),  # Unique constraint depends on table
                (
                    "i:security.users_email_key",
                    "security.users.users_email_key",
                ),  # Unique index depends on constraint
                (
                    "P:security.users.user_isolation",
                    "r:security.users",
                ),  # Policy depends on table
            ],
        ),
        (
            "multiple policies with dependencies",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                author_id INTEGER NOT NULL,
                published BOOLEAN DEFAULT false
            );
            """,
            """
            ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY;

            -- Read policy for all users
            CREATE POLICY read_posts ON app.posts
                FOR SELECT
                TO public
                USING (published = true);

            -- Insert policy for authenticated users
            CREATE POLICY insert_own_posts ON app.posts
                FOR INSERT
                TO public
                WITH CHECK (true);

            -- Update policy for authors
            CREATE POLICY update_own_posts ON app.posts
                FOR UPDATE
                TO public
                USING (true)
                WITH CHECK (true);
            """,
            [
                "ALTER TABLE",
                "ENABLE ROW LEVEL SECURITY",
                "CREATE POLICY",
                "read_posts",
                "insert_own_posts",
                "update_own_posts",
                '"app"."posts"',
                "FOR SELECT",
                "FOR INSERT",
                "FOR UPDATE",
                "TO public",
                "TO public",
                "USING",
                "WITH CHECK",
                "published = true",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:app.posts", "app"),  # Table depends on schema
                ("app.posts.posts_pkey", "r:app.posts"),  # Primary key depends on table
                (
                    "i:app.posts_pkey",
                    "app.posts.posts_pkey",
                ),  # Index depends on constraint
            ],
            # Branch dependencies (after enabling RLS and creating policies)
            [
                ("r:app.posts", "app"),  # Table depends on schema
                ("app.posts.posts_pkey", "r:app.posts"),  # Primary key depends on table
                (
                    "i:app.posts_pkey",
                    "app.posts.posts_pkey",
                ),  # Index depends on constraint
                (
                    "P:app.posts.read_posts",
                    "r:app.posts",
                ),  # Read policy depends on table
                (
                    "P:app.posts.insert_own_posts",
                    "r:app.posts",
                ),  # Insert policy depends on table
                (
                    "P:app.posts.update_own_posts",
                    "r:app.posts",
                ),  # Update policy depends on table
            ],
        ),
        (
            "create table and policy together",
            """
            CREATE SCHEMA tenant;
            """,
            """
            CREATE TABLE tenant.data (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER
            );

            ALTER TABLE tenant.data ENABLE ROW LEVEL SECURITY;

            CREATE POLICY tenant_isolation ON tenant.data
                FOR ALL
                TO public
                USING (true)
                WITH CHECK (true);
            """,
            [
                "CREATE TABLE",
                '"tenant"."data"',
                "ALTER TABLE",
                "ENABLE ROW LEVEL SECURITY",
                "CREATE POLICY",
                "tenant_isolation",
                "FOR ALL",
                "TO public",
                "USING",
                "WITH CHECK",
                "true",
            ],
            # Master dependencies (just schema)
            [],
            # Branch dependencies (after creating table and policy)
            [
                ("r:tenant.data", "tenant"),  # Table depends on schema
                (
                    "tenant.data.data_pkey",
                    "r:tenant.data",
                ),  # Primary key depends on table
                (
                    "i:tenant.data_pkey",
                    "tenant.data.data_pkey",
                ),  # Index depends on constraint
                (
                    "P:tenant.data.tenant_isolation",
                    "r:tenant.data",
                ),  # Policy depends on table
            ],
        ),
    ],
)
def test_policy_dependencies(
    session,
    alt_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test policy dependency tracking in roundtrip scenarios."""
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
