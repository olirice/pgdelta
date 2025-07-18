# Schemas

PostgreSQL schemas are namespaces that contain database objects like tables, views, functions, and types.

## PostgreSQL Specification

### CREATE SCHEMA Syntax

```sql
CREATE SCHEMA [ IF NOT EXISTS ] schema_name [ AUTHORIZATION role_specification ] [ schema_element [ ... ] ]
CREATE SCHEMA [ IF NOT EXISTS ] AUTHORIZATION role_specification [ schema_element [ ... ] ]
```

Where `role_specification` is:
```sql
[ GROUP ] role_name
| CURRENT_ROLE
| CURRENT_USER
| SESSION_USER
```

**Reference**: [PostgreSQL 17 CREATE SCHEMA](https://www.postgresql.org/docs/17/sql-createschema.html)

### DROP SCHEMA Syntax

```sql
DROP SCHEMA [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]
```

**Reference**: [PostgreSQL 17 DROP SCHEMA](https://www.postgresql.org/docs/17/sql-dropschema.html)

### ALTER SCHEMA Syntax

```sql
ALTER SCHEMA name RENAME TO new_name
ALTER SCHEMA name OWNER TO { new_owner | CURRENT_ROLE | CURRENT_USER | SESSION_USER }
```

**Reference**: [PostgreSQL 17 ALTER SCHEMA](https://www.postgresql.org/docs/17/sql-alterschema.html)

## pgdelta Support

### ✅ Currently Supported

#### CREATE SCHEMA
- Basic schema creation with schema name
- Schema dependency resolution
- Automatic ordering with other DDL statements

```sql
CREATE SCHEMA "analytics";
```

#### DROP SCHEMA
- Schema deletion
- Dependency-aware ordering (drops contents first)
- Cascade behavior handled by dependency resolution

```sql
DROP SCHEMA "analytics";
```

### ❌ Not Yet Supported

#### CREATE SCHEMA Options
- `AUTHORIZATION` clause for ownership
- Schema elements (inline object creation)

#### ALTER SCHEMA
- Owner changes (`OWNER TO`) (planned)

### 🚫 Intentionally Not Supported

#### CREATE SCHEMA
- `IF NOT EXISTS` clause (pgdelta tracks existence)

#### ALTER SCHEMA
- Schema renaming (`RENAME TO`) - uses drop/recreate pattern

#### Security and Ownership
- Schema-level privileges (security context)

## Usage Examples

### Basic Schema Creation

```python
from pgdelta import extract_catalog, generate_sql

# Source schema (empty)
source_sql = ""

# Target schema with new schema
target_sql = "CREATE SCHEMA analytics;"

# Generate diff
changes = source_catalog.diff(target_catalog)
sql = generate_sql(changes[0])
# Result: CREATE SCHEMA "analytics";
```

### Schema with Objects

```python
# Schema with table
target_sql = """
CREATE SCHEMA analytics;
CREATE TABLE analytics.metrics (
    id SERIAL PRIMARY KEY,
    value NUMERIC
);
"""

# pgdelta will generate:
# 1. CREATE SCHEMA "analytics";
# 2. CREATE TABLE "analytics"."metrics" (...);
```

### Schema Deletion

```python
# Source has schema, target doesn't
source_sql = """
CREATE SCHEMA analytics;
CREATE TABLE analytics.metrics (id SERIAL PRIMARY KEY);
"""

target_sql = ""

# pgdelta will generate (in correct order):
# 1. DROP TABLE "analytics"."metrics";
# 2. DROP SCHEMA "analytics";
```

## Implementation Details

### Schema Model

```python
@dataclass(frozen=True)
class CreateSchema:
    stable_id: str      # Format: "s:schema_name"
    nspname: str        # Schema name
```

### SQL Generation

```python
def generate_create_schema_sql(change: CreateSchema) -> str:
    """Generate CREATE SCHEMA SQL."""
    quoted_schema = f'"{change.nspname}"'
    return f"CREATE SCHEMA {quoted_schema};"
```

### Dependency Resolution

Schemas have dependencies with their contained objects:
- **CREATE**: Schema must be created before its objects
- **DROP**: Schema objects must be dropped before the schema

```python
# Dependencies for CREATE SCHEMA
depends_on = []  # Schemas have no dependencies

# Dependencies for DROP SCHEMA
depends_on = [all_objects_in_schema]  # All contained objects
```

## Testing

### Unit Tests

```python
def test_create_schema_basic():
    """Test basic schema creation."""
    change = CreateSchema(
        stable_id="s:test_schema",
        nspname="test_schema"
    )

    sql = generate_create_schema_sql(change)
    assert sql == 'CREATE SCHEMA "test_schema";'

def test_create_schema_quoted():
    """Test schema with special characters."""
    change = CreateSchema(
        stable_id="s:test-schema",
        nspname="test-schema"
    )

    sql = generate_create_schema_sql(change)
    assert sql == 'CREATE SCHEMA "test-schema";'
```

### Integration Tests

```python
def test_schema_roundtrip(postgres_session):
    """Test schema creation roundtrip fidelity."""
    # Create schema
    postgres_session.execute(text('CREATE SCHEMA "analytics"'))
    postgres_session.commit()

    # Extract catalog
    catalog = extract_catalog(postgres_session)

    # Find schema
    schema = next(s for s in catalog.schemas if s.nspname == "analytics")
    assert schema.nspname == "analytics"

    # Generate SQL
    change = CreateSchema(
        stable_id=f"s:{schema.nspname}",
        nspname=schema.nspname
    )

    sql = generate_create_schema_sql(change)
    assert 'CREATE SCHEMA "analytics"' in sql
```

### Dependency Tests

```python
def test_schema_object_dependencies():
    """Test schema dependencies with contained objects."""
    source_sql = ""
    target_sql = """
    CREATE SCHEMA app;
    CREATE TABLE app.users (id SERIAL PRIMARY KEY);
    CREATE INDEX idx_users_id ON app.users (id);
    """

    changes = generate_changes(source_sql, target_sql)

    # Should generate in correct order:
    # 1. CREATE SCHEMA "app";
    # 2. CREATE TABLE "app"."users" (...);
    # 3. CREATE INDEX "idx_users_id" ON "app"."users" (...);

    assert isinstance(changes[0], CreateSchema)
    assert isinstance(changes[1], CreateTable)
    assert isinstance(changes[2], CreateIndex)
```

## Error Handling

### Common Errors

```python
# Schema already exists
try:
    session.execute(text('CREATE SCHEMA "existing_schema"'))
except Exception as e:
    # pgdelta avoids this by tracking existence
    pass

# Schema name conflicts
try:
    session.execute(text('CREATE SCHEMA "public"'))  # Reserved name
except Exception as e:
    # pgdelta validates schema names
    pass
```

### Validation

```python
def validate_schema_name(name: str) -> bool:
    """Validate schema name according to PostgreSQL rules."""
    # Must be valid identifier
    if not name.isidentifier():
        return False

    # Check for reserved words
    reserved = {'public', 'information_schema', 'pg_catalog'}
    if name.lower() in reserved:
        return False

    return True
```

## Future Enhancements

### Planned Features (v0.2.0)

#### ALTER SCHEMA Support
```sql
-- Schema renaming
ALTER SCHEMA "old_name" RENAME TO "new_name";

-- Owner changes (if we add role support)
ALTER SCHEMA "analytics" OWNER TO analytics_user;
```

#### CREATE SCHEMA Options
```sql
-- With authorization
CREATE SCHEMA "analytics" AUTHORIZATION analytics_user;

-- With inline objects
CREATE SCHEMA "analytics"
    CREATE TABLE metrics (id SERIAL PRIMARY KEY)
    CREATE VIEW metric_summary AS SELECT COUNT(*) FROM metrics;
```

### Implementation Notes

#### Schema Renaming
Schema renaming is complex because:
- All dependent objects must be updated
- Cross-schema references must be maintained
- May be better handled as DROP/CREATE pattern

#### Authorization
Authorization support requires:
- Role tracking and resolution
- Environment-specific security context
- May be environment-specific configuration

## Best Practices

### Naming Conventions

```python
# Good schema names
good_names = [
    "public",           # Default schema
    "app",              # Application schema
    "analytics",        # Analytics schema
    "reporting",        # Reporting schema
    "staging",          # Staging schema
]

# Avoid special characters
avoid_names = [
    "app-schema",       # Hyphens require quoting
    "123schema",        # Starting with numbers
    "schema name",      # Spaces require quoting
]
```

### Schema Organization

```python
# Organize by function
schemas = {
    "app": "Core application objects",
    "analytics": "Analytics and reporting",
    "audit": "Audit and logging",
    "staging": "ETL staging area",
    "archive": "Historical data",
}

# Use consistent naming
prefixes = {
    "app_": "Application schemas",
    "rpt_": "Reporting schemas",
    "tmp_": "Temporary schemas",
}
```

### Migration Patterns

```python
# Schema creation pattern
def create_schema_with_objects():
    """Create schema and its objects in correct order."""
    return [
        "CREATE SCHEMA \"new_schema\";",
        "CREATE TABLE \"new_schema\".\"table1\" (...);",
        "CREATE INDEX \"idx_table1\" ON \"new_schema\".\"table1\" (...);",
    ]

# Schema deletion pattern
def drop_schema_with_objects():
    """Drop schema objects in reverse dependency order."""
    return [
        "DROP INDEX \"new_schema\".\"idx_table1\";",
        "DROP TABLE \"new_schema\".\"table1\";",
        "DROP SCHEMA \"new_schema\";",
    ]
```
