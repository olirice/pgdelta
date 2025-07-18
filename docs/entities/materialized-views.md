# Materialized Views

PostgreSQL materialized views are physical copies of query results that can be refreshed periodically.

## PostgreSQL Specification

### CREATE MATERIALIZED VIEW Syntax
```sql
CREATE MATERIALIZED VIEW [ IF NOT EXISTS ] table_name
    [ (column_name [, ...] ) ]
    [ USING method ]
    [ WITH ( storage_parameter [= value] [, ... ] ) ]
    [ TABLESPACE tablespace_name ]
    AS query
    [ WITH [ NO ] DATA ]
```

### DROP MATERIALIZED VIEW Syntax
```sql
DROP MATERIALIZED VIEW [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]
```

**Reference**: [PostgreSQL 17 CREATE MATERIALIZED VIEW](https://www.postgresql.org/docs/17/sql-creatematerializedview.html)

## pgdelta Support

### ✅ Currently Supported
- CREATE MATERIALIZED VIEW with AS query
- DROP MATERIALIZED VIEW
- Schema-qualified names
- Basic materialized view lifecycle

```sql
CREATE MATERIALIZED VIEW "public"."user_stats" AS
SELECT
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as user_count
FROM users
GROUP BY DATE_TRUNC('month', created_at);
```

### ❌ Not Yet Supported
- ALTER MATERIALIZED VIEW operations (planned)
- Storage parameters
- USING method
- Explicit column names

### 🚫 Intentionally Not Supported
- WITH DATA option (always uses NO DATA for safety)
- TABLESPACE clause (not applicable)
- IF EXISTS/IF NOT EXISTS (pgdelta tracks existence)
- REFRESH MATERIALIZED VIEW (not applicable for DDL)

## Usage Examples

### Basic Materialized View
```python
target_sql = """
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    total DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT now()
);

CREATE MATERIALIZED VIEW monthly_sales AS
SELECT
    DATE_TRUNC('month', created_at) as month,
    SUM(total) as total_sales,
    COUNT(*) as order_count
FROM orders
GROUP BY DATE_TRUNC('month', created_at);
"""
```

## Implementation Details

### Materialized View Models
```python
@dataclass(frozen=True)
class CreateMaterializedView:
    stable_id: str      # Format: "m:schema.matview_name"
    namespace: str      # Schema name
    relname: str        # Materialized view name
    definition: str     # Complete AS query
```

### SQL Generation
```python
def generate_create_materialized_view_sql(change: CreateMaterializedView) -> str:
    """Generate CREATE MATERIALIZED VIEW SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_matview = f'"{change.relname}"'

    return f'CREATE MATERIALIZED VIEW {quoted_schema}.{quoted_matview} AS {change.definition};'
```

## Future Enhancements

### Planned Features (v0.2.0)
- WITH/WITHOUT DATA options
- Storage parameters
- Refresh strategies
- Index management on materialized views

## Best Practices

### When to Use Materialized Views
```python
use_cases = {
    "expensive_aggregations": "Pre-compute complex GROUP BY queries",
    "reporting": "Snapshot data for reports",
    "denormalization": "Flatten normalized data for performance",
    "external_data": "Cache data from foreign data wrappers"
}

avoid_cases = {
    "frequently_updated": "High update frequency makes refresh costly",
    "simple_queries": "Regular views are sufficient",
    "real_time_data": "Staleness is unacceptable"
}
```

### Refresh Strategies
```python
# Manual refresh patterns (outside pgdelta scope)
refresh_patterns = {
    "scheduled": "CRON job with REFRESH MATERIALIZED VIEW",
    "triggered": "Refresh on base table changes",
    "concurrent": "REFRESH MATERIALIZED VIEW CONCURRENTLY",
    "partial": "Incremental refresh patterns"
}
```
