"""Test ALTER POLICY SQL generation."""

from pgdelta.changes import AlterPolicy, RenamePolicyTo
from pgdelta.changes.dispatcher import generate_sql


def test_rename_policy_basic():
    """Test ALTER POLICY RENAME TO with basic names."""
    change = RenamePolicyTo(
        stable_id="P:public.users.old_policy",
        namespace="public",
        tablename="users",
        old_name="old_policy",
        new_name="new_policy",
    )

    sql = generate_sql(change)

    assert (
        sql == 'ALTER POLICY "old_policy" ON "public"."users" RENAME TO "new_policy";'
    )


def test_rename_policy_complex_schema():
    """Test ALTER POLICY RENAME TO with complex schema and table names."""
    change = RenamePolicyTo(
        stable_id="P:auth.user_sessions.user_isolation_policy",
        namespace="auth",
        tablename="user_sessions",
        old_name="user_isolation_policy",
        new_name="session_isolation_policy",
    )

    sql = generate_sql(change)

    assert (
        sql
        == 'ALTER POLICY "user_isolation_policy" ON "auth"."user_sessions" RENAME TO "session_isolation_policy";'
    )


def test_alter_policy_roles_only():
    """Test ALTER POLICY with only role changes."""
    change = AlterPolicy(
        stable_id="P:public.users.user_policy",
        namespace="public",
        tablename="users",
        policy_name="user_policy",
        new_roles=["authenticated", "admin"],
        new_using=None,
        new_with_check=None,
    )

    sql = generate_sql(change)

    assert (
        sql == 'ALTER POLICY "user_policy" ON "public"."users" TO authenticated, admin;'
    )


def test_alter_policy_using_only():
    """Test ALTER POLICY with only USING expression change."""
    change = AlterPolicy(
        stable_id="P:public.users.user_policy",
        namespace="public",
        tablename="users",
        policy_name="user_policy",
        new_roles=None,
        new_using="auth.uid() = id",
        new_with_check=None,
    )

    sql = generate_sql(change)

    assert (
        sql == 'ALTER POLICY "user_policy" ON "public"."users" USING (auth.uid() = id);'
    )


def test_alter_policy_with_check_only():
    """Test ALTER POLICY with only WITH CHECK expression change."""
    change = AlterPolicy(
        stable_id="P:public.posts.insert_policy",
        namespace="public",
        tablename="posts",
        policy_name="insert_policy",
        new_roles=None,
        new_using=None,
        new_with_check="auth.uid() = author_id",
    )

    sql = generate_sql(change)

    assert (
        sql
        == 'ALTER POLICY "insert_policy" ON "public"."posts" WITH CHECK (auth.uid() = author_id);'
    )


def test_alter_policy_all_changes():
    """Test ALTER POLICY with all possible changes."""
    change = AlterPolicy(
        stable_id="P:app.data.data_policy",
        namespace="app",
        tablename="data",
        policy_name="data_policy",
        new_roles=["public", "authenticated"],
        new_using="tenant_id = current_tenant_id()",
        new_with_check="tenant_id = current_tenant_id() AND created_by = auth.uid()",
    )

    sql = generate_sql(change)

    expected = (
        'ALTER POLICY "data_policy" ON "app"."data" '
        "TO public, authenticated "
        "USING (tenant_id = current_tenant_id()) "
        "WITH CHECK (tenant_id = current_tenant_id() AND created_by = auth.uid());"
    )
    assert sql == expected


def test_alter_policy_public_role():
    """Test ALTER POLICY with PUBLIC role."""
    change = AlterPolicy(
        stable_id="P:public.users.user_policy",
        namespace="public",
        tablename="users",
        policy_name="user_policy",
        new_roles=["PUBLIC"],
        new_using=None,
        new_with_check=None,
    )

    sql = generate_sql(change)

    assert sql == 'ALTER POLICY "user_policy" ON "public"."users" TO PUBLIC;'


def test_alter_policy_current_user():
    """Test ALTER POLICY with special PostgreSQL roles."""
    change = AlterPolicy(
        stable_id="P:secure.data.admin_policy",
        namespace="secure",
        tablename="data",
        policy_name="admin_policy",
        new_roles=["CURRENT_USER", "SESSION_USER"],
        new_using=None,
        new_with_check=None,
    )

    sql = generate_sql(change)

    assert (
        sql
        == 'ALTER POLICY "admin_policy" ON "secure"."data" TO CURRENT_USER, SESSION_USER;'
    )


def test_alter_policy_complex_expressions():
    """Test ALTER POLICY with complex SQL expressions."""
    change = AlterPolicy(
        stable_id="P:analytics.events.filter_policy",
        namespace="analytics",
        tablename="events",
        policy_name="filter_policy",
        new_roles=None,
        new_using="date_part('year', created_at) >= 2023 AND user_id IN (SELECT id FROM authorized_users)",
        new_with_check="created_at <= NOW() AND event_type IN ('click', 'view', 'conversion')",
    )

    sql = generate_sql(change)

    expected = (
        'ALTER POLICY "filter_policy" ON "analytics"."events" '
        "USING (date_part('year', created_at) >= 2023 AND user_id IN (SELECT id FROM authorized_users)) "
        "WITH CHECK (created_at <= NOW() AND event_type IN ('click', 'view', 'conversion'));"
    )
    assert sql == expected
