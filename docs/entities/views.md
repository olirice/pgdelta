# Views

PostgreSQL views are virtual tables that provide a dynamic window into data from one or more tables.

## PostgreSQL Specification

### CREATE VIEW Syntax
```sql
CREATE [ OR REPLACE ] [ TEMP | TEMPORARY ] [ RECURSIVE ] VIEW name [ ( column_name [, ...] ) ]
    [ WITH ( view_option_name [= view_option_value] [, ... ] ) ]
    AS query
    [ WITH [ CASCADED | LOCAL ] CHECK OPTION ]
```

### DROP VIEW Syntax
```sql
DROP VIEW [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]
```

**Reference**: [PostgreSQL 17 CREATE VIEW](https://www.postgresql.org/docs/17/sql-createview.html)

## pgdelta Support

### ✅ Currently Supported
- CREATE VIEW with AS query
- DROP VIEW
- CREATE OR REPLACE VIEW
- Schema-qualified view names

```sql
CREATE VIEW "public"."active_users" AS
SELECT id, email, created_at
FROM users
WHERE is_active = true;
```

### ❌ Not Yet Supported
- RECURSIVE views
- Explicit column names
- WITH CHECK OPTION
- View options (security_barrier, check_option)

### 🚫 Intentionally Not Supported
- TEMPORARY views (not persistent schema objects)
- IF EXISTS/IF NOT EXISTS (pgdelta tracks existence)

## Usage Examples

### Basic View Creation
```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT,
    is_active BOOLEAN DEFAULT true
);

CREATE VIEW active_users AS
SELECT id, email FROM users WHERE is_active = true;
"""
```

### View Replacement
```python
# Change view definition
source_sql = """
CREATE VIEW user_summary AS
SELECT id, email FROM users;
"""

target_sql = """
CREATE VIEW user_summary AS
SELECT id, email, created_at FROM users;
"""
# Results in: CREATE OR REPLACE VIEW "public"."user_summary" AS ...
```

## Implementation Details

### View Models
```python
@dataclass(frozen=True)
class CreateView:
    stable_id: str      # Format: "v:schema.view_name"
    namespace: str      # Schema name
    relname: str        # View name
    definition: str     # Complete view definition (AS query)

@dataclass(frozen=True)
class ReplaceView:
    stable_id: str      # Format: "v:schema.view_name"
    namespace: str      # Schema name
    relname: str        # View name
    definition: str     # New view definition
```

### SQL Generation
```python
def generate_create_view_sql(change: CreateView) -> str:
    """Generate CREATE VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_view = f'"{change.relname}"'

    return f'CREATE VIEW {quoted_schema}.{quoted_view} AS {change.definition};'

def generate_replace_view_sql(change: ReplaceView) -> str:
    """Generate CREATE OR REPLACE VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_view = f'"{change.relname}"'

    return f'CREATE OR REPLACE VIEW {quoted_schema}.{quoted_view} AS {change.definition};'
```

## Future Enhancements

### Planned Features (v0.2.0)
- RECURSIVE views
- View column aliases
- WITH CHECK OPTION
- View dependencies tracking

## Best Practices

### View Naming
```python
# Good view names
good_names = [
    "active_users",           # Descriptive of content
    "user_summary",           # Summarizes data
    "recent_orders",          # Time-based views
    "monthly_sales_report",   # Reporting views
]

# Avoid table-like names
avoid_names = [
    "users_view",             # Redundant suffix
    "vw_users",               # Hungarian notation
    "temp_users",             # Confusing with temporary
]
```

### Performance Considerations
```python
# View performance guidelines
performance_tips = {
    "simple_views": "Fast, just query rewriting",
    "complex_joins": "Consider materialized views",
    "aggregations": "May benefit from indexes on base tables",
    "nested_views": "Avoid views of views when possible"
}
```
