"""Integration tests for RLS (Row Level Security) operations."""

import pytest
from tests.integration.roundtrip import roundtrip_fidelity_test


@pytest.mark.integration
@pytest.mark.roundtrip
@pytest.mark.parametrize(
    "test_name,initial_setup,test_sql,expected_terms,expected_master_dependencies,expected_branch_dependencies",
    [
        (
            "enable RLS on table",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            """,
            """
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            """,
            [
                'ALTER TABLE "app"."users" ENABLE ROW LEVEL SECURITY',
            ],
            # Master dependencies (initial setup)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
            # Branch dependencies (after enabling RLS)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
        ),
        (
            "disable RLS on table",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            """,
            """
            ALTER TABLE app.users DISABLE ROW LEVEL SECURITY;
            """,
            [
                'ALTER TABLE "app"."users" DISABLE ROW LEVEL SECURITY',
            ],
            # Master dependencies (table with RLS enabled)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
            # Branch dependencies (after disabling RLS)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
        ),
        (
            "create basic RLS policy",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            """,
            """
            CREATE POLICY user_isolation ON app.users
                FOR ALL
                TO public
                USING (true);
            """,
            [
                "CREATE POLICY",
                "user_isolation",
                '"app"."users"',
                "FOR ALL",
                "TO public",
                "USING",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
            # Branch dependencies (after creating policy)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
                ("P:app.users.user_isolation", "r:app.users"),
            ],
        ),
        (
            "create policy with WITH CHECK",
            """
            CREATE SCHEMA blog;
            CREATE TABLE blog.posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                author_id INTEGER NOT NULL,
                published BOOLEAN DEFAULT false
            );
            ALTER TABLE blog.posts ENABLE ROW LEVEL SECURITY;
            """,
            """
            CREATE POLICY insert_own_posts ON blog.posts
                FOR INSERT
                TO public
                WITH CHECK (true);
            """,
            [
                "CREATE POLICY",
                "insert_own_posts",
                '"blog"."posts"',
                "FOR INSERT",
                "TO public",
                "WITH CHECK",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:blog.posts", "blog"),
                ("blog.posts.posts_pkey", "r:blog.posts"),
                ("i:blog.posts_pkey", "blog.posts.posts_pkey"),
            ],
            # Branch dependencies (after creating policy)
            [
                ("r:blog.posts", "blog"),
                ("blog.posts.posts_pkey", "r:blog.posts"),
                ("i:blog.posts_pkey", "blog.posts.posts_pkey"),
                ("P:blog.posts.insert_own_posts", "r:blog.posts"),
            ],
        ),
        (
            "create RESTRICTIVE policy",
            """
            CREATE SCHEMA secure;
            CREATE TABLE secure.sensitive_data (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                classification TEXT NOT NULL
            );
            ALTER TABLE secure.sensitive_data ENABLE ROW LEVEL SECURITY;
            """,
            """
            CREATE POLICY admin_only ON secure.sensitive_data
                AS RESTRICTIVE
                FOR SELECT
                TO public
                USING (true);
            """,
            [
                "CREATE POLICY",
                "admin_only",
                '"secure"."sensitive_data"',
                "AS RESTRICTIVE",
                "FOR SELECT",
                "TO public",
                "USING",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:secure.sensitive_data", "secure"),
                (
                    "secure.sensitive_data.sensitive_data_pkey",
                    "r:secure.sensitive_data",
                ),
                (
                    "i:secure.sensitive_data_pkey",
                    "secure.sensitive_data.sensitive_data_pkey",
                ),
            ],
            # Branch dependencies (after creating policy)
            [
                ("r:secure.sensitive_data", "secure"),
                (
                    "secure.sensitive_data.sensitive_data_pkey",
                    "r:secure.sensitive_data",
                ),
                (
                    "i:secure.sensitive_data_pkey",
                    "secure.sensitive_data.sensitive_data_pkey",
                ),
                ("P:secure.sensitive_data.admin_only", "r:secure.sensitive_data"),
            ],
        ),
        (
            "drop RLS policy",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            );
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            CREATE POLICY user_isolation ON app.users
                FOR ALL
                TO public
                USING (true);
            """,
            """
            DROP POLICY user_isolation ON app.users;
            """,
            [
                "DROP POLICY",
                "user_isolation",
                '"app"."users"',
            ],
            # Master dependencies (table with policy before drop)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
                (
                    "P:app.users.user_isolation",
                    "r:app.users",
                ),  # Policy dependency exists in master catalog
            ],
            # Branch dependencies (after dropping policy)
            [
                ("r:app.users", "app"),
                ("app.users.users_email_key", "r:app.users"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_email_key", "app.users.users_email_key"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
        ),
        (
            "multiple policies on same table",
            """
            CREATE SCHEMA forum;
            CREATE TABLE forum.messages (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                thread_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE forum.messages ENABLE ROW LEVEL SECURITY;
            """,
            """
            -- Read policy: users can read all messages
            CREATE POLICY read_messages ON forum.messages
                FOR SELECT
                TO public
                USING (true);

            -- Insert policy: users can only insert their own messages
            CREATE POLICY insert_own_messages ON forum.messages
                FOR INSERT
                TO public
                WITH CHECK (true);

            -- Update policy: users can only update their own messages
            CREATE POLICY update_own_messages ON forum.messages
                FOR UPDATE
                TO public
                USING (true)
                WITH CHECK (true);
            """,
            [
                "CREATE POLICY",
                "read_messages",
                "insert_own_messages",
                "update_own_messages",
                '"forum"."messages"',
                "FOR SELECT",
                "FOR INSERT",
                "FOR UPDATE",
                "TO public",
                "USING (true)",
                "WITH CHECK",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:forum.messages", "forum"),
                ("forum.messages.messages_pkey", "r:forum.messages"),
                ("i:forum.messages_pkey", "forum.messages.messages_pkey"),
            ],
            # Branch dependencies (after creating multiple policies)
            [
                ("r:forum.messages", "forum"),
                ("forum.messages.messages_pkey", "r:forum.messages"),
                ("i:forum.messages_pkey", "forum.messages.messages_pkey"),
                ("P:forum.messages.read_messages", "r:forum.messages"),
                ("P:forum.messages.insert_own_messages", "r:forum.messages"),
                ("P:forum.messages.update_own_messages", "r:forum.messages"),
            ],
        ),
        (
            "complete RLS setup with policies",
            """
            CREATE SCHEMA tenant;
            """,
            """
            -- Create a multi-tenant table
            CREATE TABLE tenant.data (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_by INTEGER NOT NULL
            );

            -- Enable RLS
            ALTER TABLE tenant.data ENABLE ROW LEVEL SECURITY;

            -- Create tenant isolation policy
            CREATE POLICY tenant_isolation ON tenant.data
                FOR ALL
                TO public
                USING (true)
                WITH CHECK (true);

            -- Create admin bypass policy (PERMISSIVE - default)
            CREATE POLICY admin_bypass ON tenant.data
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
                "admin_bypass",
                "FOR ALL",
                "TO public",
                "true",
                "USING (true)",
                "WITH CHECK (true)",
            ],
            # Master dependencies (initial setup with just schema)
            [],
            # Branch dependencies (after creating table, enabling RLS, and adding policies)
            [
                ("r:tenant.data", "tenant"),
                ("tenant.data.data_pkey", "r:tenant.data"),
                ("i:tenant.data_pkey", "tenant.data.data_pkey"),
                ("P:tenant.data.tenant_isolation", "r:tenant.data"),
                ("P:tenant.data.admin_bypass", "r:tenant.data"),
            ],
        ),
        (
            "enable RLS on simple table",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            """,
            """
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            """,
            [
                'ALTER TABLE "app"."users" ENABLE ROW LEVEL SECURITY',
            ],
            # Master dependencies (initial setup)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
            # Branch dependencies (after enabling RLS)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
        ),
        (
            "disable RLS on simple table",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            """,
            """
            ALTER TABLE app.users DISABLE ROW LEVEL SECURITY;
            """,
            [
                'ALTER TABLE "app"."users" DISABLE ROW LEVEL SECURITY',
            ],
            # Master dependencies (table with RLS enabled)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
            # Branch dependencies (after disabling RLS)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
        ),
        (
            "create basic RLS policy on simple table",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            """,
            """
            CREATE POLICY user_policy ON app.users
                FOR ALL
                TO public
                USING (true);
            """,
            [
                "CREATE POLICY",
                "user_policy",
                '"app"."users"',
                "FOR ALL",
                "TO public",
                "USING",
                "true",
            ],
            # Master dependencies (initial setup)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
            # Branch dependencies (after creating policy)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
                ("P:app.users.user_policy", "r:app.users"),
            ],
        ),
        (
            "drop RLS policy from simple table",
            """
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
            CREATE POLICY user_policy ON app.users
                FOR ALL
                TO public
                USING (true);
            """,
            """
            DROP POLICY user_policy ON app.users;
            """,
            [
                "DROP POLICY",
                "user_policy",
                '"app"."users"',
            ],
            # Master dependencies (table with policy before drop)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
                (
                    "P:app.users.user_policy",
                    "r:app.users",
                ),  # Policy dependency exists in master catalog
            ],
            # Branch dependencies (after dropping policy)
            [
                ("r:app.users", "app"),
                ("app.users.users_pkey", "r:app.users"),
                ("i:app.users_pkey", "app.users.users_pkey"),
            ],
        ),
    ],
)
def test_rls_operations(
    session,
    alt_session,
    test_name,
    initial_setup,
    test_sql,
    expected_terms,
    expected_master_dependencies,
    expected_branch_dependencies,
):
    """Test RLS operations roundtrip fidelity."""
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
