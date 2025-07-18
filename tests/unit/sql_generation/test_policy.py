"""Test RLS policy SQL generation."""

from pgdelta.changes import CreatePolicy, DropPolicy
from pgdelta.changes.dispatcher import generate_sql
from pgdelta.model import PgPolicy


def test_create_policy_basic():
    """Test CREATE POLICY with basic USING expression."""
    policy = PgPolicy(
        polname="user_isolation",
        tablename="users",
        namespace="public",
        polcmd="ALL",
        polpermissive=True,
        polroles=["authenticated"],
        polqual="(auth.uid() = user_id)",
        polwithcheck=None,
        oid=16384,
    )

    change = CreatePolicy(
        stable_id="P:public.users.user_isolation",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "user_isolation" ON "public"."users"' in sql
    assert "AS PERMISSIVE" in sql
    assert "FOR ALL" in sql
    assert 'TO "authenticated"' in sql
    assert "USING ((auth.uid() = user_id))" in sql
    assert "WITH CHECK" not in sql
    assert sql.endswith(";")


def test_create_policy_restrictive():
    """Test CREATE POLICY with RESTRICTIVE policy."""
    policy = PgPolicy(
        polname="admin_only",
        tablename="sensitive_data",
        namespace="private",
        polcmd="SELECT",
        polpermissive=False,
        polroles=["admin"],
        polqual="(auth.has_role('admin'))",
        polwithcheck=None,
        oid=16385,
    )

    change = CreatePolicy(
        stable_id="P:private.sensitive_data.admin_only",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "admin_only" ON "private"."sensitive_data"' in sql
    assert "AS RESTRICTIVE" in sql
    assert "FOR SELECT" in sql
    assert 'TO "admin"' in sql
    assert "USING ((auth.has_role('admin')))" in sql
    assert sql.endswith(";")


def test_create_policy_with_check():
    """Test CREATE POLICY with both USING and WITH CHECK expressions."""
    policy = PgPolicy(
        polname="insert_own_posts",
        tablename="posts",
        namespace="public",
        polcmd="INSERT",
        polpermissive=True,
        polroles=["authenticated"],
        polqual=None,
        polwithcheck="(auth.uid() = author_id)",
        oid=16386,
    )

    change = CreatePolicy(
        stable_id="P:public.posts.insert_own_posts",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "insert_own_posts" ON "public"."posts"' in sql
    assert "AS PERMISSIVE" in sql
    assert "FOR INSERT" in sql
    assert 'TO "authenticated"' in sql
    assert "USING" not in sql
    assert "WITH CHECK ((auth.uid() = author_id))" in sql
    assert sql.endswith(";")


def test_create_policy_update_with_both():
    """Test CREATE POLICY for UPDATE with both USING and WITH CHECK."""
    policy = PgPolicy(
        polname="update_own_posts",
        tablename="posts",
        namespace="public",
        polcmd="UPDATE",
        polpermissive=True,
        polroles=["authenticated"],
        polqual="(auth.uid() = author_id)",
        polwithcheck="(auth.uid() = author_id AND status != 'published')",
        oid=16387,
    )

    change = CreatePolicy(
        stable_id="P:public.posts.update_own_posts",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "update_own_posts" ON "public"."posts"' in sql
    assert "AS PERMISSIVE" in sql
    assert "FOR UPDATE" in sql
    assert 'TO "authenticated"' in sql
    assert "USING ((auth.uid() = author_id))" in sql
    assert "WITH CHECK ((auth.uid() = author_id AND status != 'published'))" in sql
    assert sql.endswith(";")


def test_create_policy_multiple_roles():
    """Test CREATE POLICY with multiple roles."""
    policy = PgPolicy(
        polname="moderator_access",
        tablename="comments",
        namespace="public",
        polcmd="ALL",
        polpermissive=True,
        polroles=["moderator", "admin", "super_admin"],
        polqual="true",
        polwithcheck="true",
        oid=16388,
    )

    change = CreatePolicy(
        stable_id="P:public.comments.moderator_access",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "moderator_access" ON "public"."comments"' in sql
    assert "AS PERMISSIVE" in sql
    assert "FOR ALL" in sql
    assert 'TO "moderator", "admin", "super_admin"' in sql
    assert "USING (true)" in sql
    assert "WITH CHECK (true)" in sql
    assert sql.endswith(";")


def test_create_policy_public_role():
    """Test CREATE POLICY with public role (no quotes)."""
    policy = PgPolicy(
        polname="public_read",
        tablename="articles",
        namespace="public",
        polcmd="SELECT",
        polpermissive=True,
        polroles=["public"],
        polqual="(published = true)",
        polwithcheck=None,
        oid=16389,
    )

    change = CreatePolicy(
        stable_id="P:public.articles.public_read",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "public_read" ON "public"."articles"' in sql
    assert "AS PERMISSIVE" in sql
    assert "FOR SELECT" in sql
    assert "TO public" in sql  # public should not be quoted
    assert "USING ((published = true))" in sql
    assert sql.endswith(";")


def test_create_policy_special_roles():
    """Test CREATE POLICY with special PostgreSQL roles."""
    policy = PgPolicy(
        polname="session_access",
        tablename="user_sessions",
        namespace="auth",
        polcmd="ALL",
        polpermissive=True,
        polroles=["current_user", "session_user"],
        polqual="(user_id = current_user_id())",
        polwithcheck=None,
        oid=16390,
    )

    change = CreatePolicy(
        stable_id="P:auth.user_sessions.session_access",
        policy=policy,
    )

    sql = generate_sql(change)

    assert 'CREATE POLICY "session_access" ON "auth"."user_sessions"' in sql
    assert "TO current_user, session_user" in sql  # special roles should not be quoted
    assert sql.endswith(";")


def test_drop_policy():
    """Test DROP POLICY SQL generation."""
    change = DropPolicy(
        stable_id="P:public.users.user_isolation",
        namespace="public",
        tablename="users",
        polname="user_isolation",
    )

    sql = generate_sql(change)

    assert sql == 'DROP POLICY "user_isolation" ON "public"."users";'
