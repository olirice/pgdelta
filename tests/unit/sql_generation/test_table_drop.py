"""DROP TABLE SQL generation tests."""

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.table import DropTable


def test_drop_table_basic():
    """Test basic DROP TABLE SQL generation."""
    change = DropTable(
        stable_id="r:test_schema.users",
        namespace="test_schema",
        relname="users",
    )

    sql = generate_sql(change)

    assert 'DROP TABLE "test_schema"."users"' in sql
    assert sql.endswith(";")


# CASCADE functionality intentionally removed - dependency resolution handles ordering
