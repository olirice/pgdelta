# Indexes

PostgreSQL indexes improve query performance by providing faster data access paths.

## PostgreSQL Specification

### CREATE INDEX Syntax

```sql
CREATE [ UNIQUE ] INDEX [ CONCURRENTLY ] [ [ IF NOT EXISTS ] name ]
ON [ ONLY ] table_name [ USING method ]
(
    { column_name | ( expression ) }
    [ COLLATE collation ]
    [ opclass [ ( opclass_parameter = value [, ...] ) ] ]
    [ ASC | DESC ]
    [ NULLS { FIRST | LAST } ]
    [, ...]
)
[ INCLUDE ( column_name [, ...] ) ]
[ NULLS [ NOT ] DISTINCT ]
[ WITH ( storage_parameter = value [, ...] ) ]
[ TABLESPACE tablespace_name ]
[ WHERE predicate ]
```

**Reference**: [PostgreSQL 17 CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)

### DROP INDEX Syntax

```sql
DROP INDEX [ CONCURRENTLY ] [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]
```

**Reference**: [PostgreSQL 17 DROP INDEX](https://www.postgresql.org/docs/17/sql-dropindex.html)

## pgdelta Support

### ✅ Currently Supported

#### CREATE INDEX
- Regular indexes (B-tree, Hash, GIN, GiST, SP-GiST, BRIN)
- Unique indexes
- Partial indexes with WHERE clause
- Functional indexes with expressions
- Multi-column indexes
- Custom operator classes
- Collation specifications
- ASC/DESC ordering options
- NULLS FIRST/LAST options
- Storage parameters (WITH clause)

```sql
-- Regular index
CREATE INDEX "idx_users_email" ON "public"."users" ("email");

-- Unique index
CREATE UNIQUE INDEX "idx_users_email_unique" ON "public"."users" ("email");

-- Partial index
CREATE INDEX "idx_active_users" ON "public"."users" ("email") WHERE is_active = true;

-- Functional index
CREATE INDEX "idx_users_email_lower" ON "public"."users" (lower("email"));

-- Multi-column index
CREATE INDEX "idx_users_name" ON "public"."users" ("last_name", "first_name");
```

#### DROP INDEX
- Index deletion
- Cascade behavior through dependency resolution

```sql
DROP INDEX "public"."idx_users_email";
```

### ❌ Not Yet Supported

#### CREATE INDEX Options
- INCLUDE columns (covering indexes)
- NULLS [NOT] DISTINCT option
- ONLY modifier for inheritance
- TABLESPACE clause
- Operator class parameters

#### ALTER INDEX Operations
- Index renaming
- Storage parameter modifications
- Tablespace changes

### 🚫 Intentionally Not Supported

#### Operational Features
- CONCURRENTLY option (not needed for schema migration)
- IF NOT EXISTS (pgdelta tracks existence)
- IF EXISTS (pgdelta tracks existence)

#### Environment-Specific Features
- TABLESPACE clause (file system layout)

## Usage Examples

### Basic Index Creation

```python
from pgdelta import extract_catalog, generate_sql

# Target schema with new index
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL
);
CREATE INDEX idx_users_email ON users (email);
"""

# Generate diff
changes = source_catalog.diff(target_catalog)
# Results in:
# 1. CREATE TABLE "public"."users" (...)
# 2. CREATE INDEX "idx_users_email" ON "public"."users" ("email");
```

### Unique Index

```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_users_email_unique ON users (email);
"""

# pgdelta generates:
# CREATE UNIQUE INDEX "idx_users_email_unique" ON "public"."users" ("email");
```

### Partial Index

```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true
);
CREATE INDEX idx_active_users ON users (email) WHERE is_active = true;
"""

# pgdelta generates:
# CREATE INDEX "idx_active_users" ON "public"."users" ("email") WHERE is_active = true;
```

### Functional Index

```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL
);
CREATE INDEX idx_users_email_lower ON users (lower(email));
"""

# pgdelta generates:
# CREATE INDEX "idx_users_email_lower" ON "public"."users" (lower(email));
```

### Multi-Column Index

```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL
);
CREATE INDEX idx_users_name ON users (last_name, first_name);
"""

# pgdelta generates:
# CREATE INDEX "idx_users_name" ON "public"."users" ("last_name", "first_name");
```

## Implementation Details

### Index Model

```python
@dataclass(frozen=True)
class CreateIndex:
    stable_id: str      # Format: "i:schema.index_name"
    index: PgIndex      # Index definition
```

### PgIndex Model

```python
@dataclass(frozen=True)
class PgIndex:
    indexname: str                 # Index name
    tablename: str                 # Table name
    schemaname: str               # Schema name
    index_definition: str          # Complete CREATE INDEX statement
    is_unique: bool               # Unique index flag
    is_primary: bool              # Primary key index flag
    is_exclusion: bool            # Exclusion constraint index flag
    
    @property
    def stable_id(self) -> str:
        """Stable identifier for cross-database comparison."""
        return f"i:{self.schemaname}.{self.indexname}"
```

### SQL Generation

```python
def generate_create_index_sql(change: CreateIndex) -> str:
    """Generate CREATE INDEX SQL from the stored index definition."""
    # PostgreSQL's pg_get_indexdef() returns the complete CREATE INDEX statement
    index_def = change.index.index_definition
    
    # Ensure it ends with a semicolon
    if not index_def.endswith(";"):
        index_def += ";"
    
    return index_def
```

## Index Types

### B-tree Indexes (Default)

```sql
-- Implicit B-tree
CREATE INDEX idx_users_id ON users (id);

-- Explicit B-tree
CREATE INDEX idx_users_id ON users USING btree (id);
```

**Use cases:**
- Equality and range queries
- ORDER BY operations
- < > <= >= operations

### Hash Indexes

```sql
CREATE INDEX idx_users_email ON users USING hash (email);
```

**Use cases:**
- Equality queries only
- Faster than B-tree for equality
- No ordering support

### GIN Indexes

```sql
-- For JSON data
CREATE INDEX idx_users_metadata ON users USING gin (metadata);

-- For full-text search
CREATE INDEX idx_users_search ON users USING gin (to_tsvector('english', name));

-- For arrays
CREATE INDEX idx_users_tags ON users USING gin (tags);
```

**Use cases:**
- JSON/JSONB data
- Full-text search
- Array operations
- Composite values

### GiST Indexes

```sql
-- For geometric data
CREATE INDEX idx_locations_point ON locations USING gist (location);

-- For full-text search
CREATE INDEX idx_users_search ON users USING gist (to_tsvector('english', name));
```

**Use cases:**
- Geometric data types
- Full-text search
- Range types
- Custom data types

### SP-GiST Indexes

```sql
-- For geometric data
CREATE INDEX idx_locations_point ON locations USING spgist (location);

-- For IP addresses
CREATE INDEX idx_logs_ip ON logs USING spgist (ip_address);
```

**Use cases:**
- Non-balanced data structures
- Geometric data
- Text patterns
- IP addresses

### BRIN Indexes

```sql
-- For time-series data
CREATE INDEX idx_logs_timestamp ON logs USING brin (created_at);

-- For sequential data
CREATE INDEX idx_orders_date ON orders USING brin (order_date);
```

**Use cases:**
- Very large tables
- Sequential data
- Time-series data
- Minimal storage overhead

## Testing

### Unit Tests

```python
def test_create_index_basic():
    """Test basic index creation."""
    index = PgIndex(
        indexname="idx_users_email",
        tablename="users",
        schemaname="public",
        index_definition='CREATE INDEX "idx_users_email" ON "public"."users" ("email")',
        is_unique=False,
        is_primary=False,
        is_exclusion=False
    )
    
    change = CreateIndex(
        stable_id="i:public.idx_users_email",
        index=index
    )
    
    sql = generate_create_index_sql(change)
    assert 'CREATE INDEX "idx_users_email"' in sql
    assert 'ON "public"."users"' in sql
```

### Integration Tests

```python
def test_index_roundtrip(postgres_session):
    """Test index creation roundtrip fidelity."""
    # Create table and index
    postgres_session.execute(text("""
        CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL
        );
        CREATE INDEX idx_test_email ON test_table (email);
    """))
    postgres_session.commit()
    
    # Extract catalog
    catalog = extract_catalog(postgres_session)
    
    # Find index
    index = next(i for i in catalog.indexes if i.indexname == "idx_test_email")
    assert index.tablename == "test_table"
    assert index.schemaname == "public"
    assert not index.is_unique
```

### Performance Tests

```python
def test_index_performance():
    """Test that indexes improve query performance."""
    # Create table with data
    postgres_session.execute(text("""
        CREATE TABLE perf_test (
            id SERIAL PRIMARY KEY,
            value INTEGER
        );
        INSERT INTO perf_test (value) 
        SELECT generate_series(1, 100000);
    """))
    
    # Test query without index
    explain_result = postgres_session.execute(text("""
        EXPLAIN (FORMAT JSON) SELECT * FROM perf_test WHERE value = 50000
    """))
    
    # Should use sequential scan
    plan = explain_result.fetchone()[0]
    assert "Seq Scan" in str(plan)
    
    # Add index
    postgres_session.execute(text("""
        CREATE INDEX idx_perf_value ON perf_test (value);
    """))
    
    # Test query with index
    explain_result = postgres_session.execute(text("""
        EXPLAIN (FORMAT JSON) SELECT * FROM perf_test WHERE value = 50000
    """))
    
    # Should use index scan
    plan = explain_result.fetchone()[0]
    assert "Index Scan" in str(plan)
```

## Advanced Features

### Operator Classes

```python
target_sql = """
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT
);

-- Use specific operator class
CREATE INDEX idx_documents_content ON documents USING gin (content gin_trgm_ops);
"""

# pgdelta preserves operator class specifications
```

### Collation Support

```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT
);

-- Index with collation
CREATE INDEX idx_users_name_collate ON users (name COLLATE "C");
"""

# pgdelta preserves collation specifications
```

### Storage Parameters

```python
target_sql = """
CREATE TABLE large_table (
    id BIGSERIAL PRIMARY KEY,
    data TEXT
);

-- Index with storage parameters
CREATE INDEX idx_large_data ON large_table (data) WITH (fillfactor = 70);
"""

# pgdelta preserves storage parameters
```

## Performance Considerations

### Index Selection Guidelines

```python
# When to use each index type
index_guidelines = {
    "btree": "Default choice for most queries",
    "hash": "Equality queries only, faster than btree",
    "gin": "JSON, arrays, full-text search",
    "gist": "Geometric data, range types",
    "spgist": "Non-balanced data, IP addresses",
    "brin": "Very large tables, sequential data"
}
```

### Index Maintenance

```python
# Monitor index usage
monitor_queries = {
    "unused_indexes": """
        SELECT schemaname, tablename, indexname, idx_scan
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        ORDER BY schemaname, tablename, indexname;
    """,
    
    "index_size": """
        SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
        FROM pg_stat_user_indexes
        ORDER BY pg_relation_size(indexrelid) DESC;
    """,
    
    "duplicate_indexes": """
        SELECT i1.schemaname, i1.tablename, i1.indexname, i2.indexname
        FROM pg_stat_user_indexes i1
        JOIN pg_stat_user_indexes i2 ON i1.tablename = i2.tablename
        WHERE i1.indexname < i2.indexname;
    """
}
```

## Error Handling

### Common Errors

```python
# Index name conflicts
try:
    sql = 'CREATE INDEX "existing_index" ON table1 (column1);'
    # pgdelta avoids this by tracking existence
except Exception as e:
    pass

# Invalid expressions
try:
    sql = 'CREATE INDEX idx_invalid ON table1 (invalid_function(column1));'
    # pgdelta validates expressions during extraction
except Exception as e:
    pass
```

### Validation

```python
def validate_index_expression(expression: str) -> bool:
    """Validate index expression syntax."""
    # Check for common issues
    if "SELECT" in expression.upper():
        return False  # Subqueries not allowed
    
    if expression.count("(") != expression.count(")"):
        return False  # Unmatched parentheses
    
    return True
```

## Future Enhancements

### Planned Features (v0.2.0)

#### INCLUDE Columns
```sql
-- Covering indexes
CREATE INDEX idx_users_email_include ON users (email) INCLUDE (first_name, last_name);
```

#### NULLS DISTINCT
```sql
-- Unique index with null handling
CREATE UNIQUE INDEX idx_users_email_nulls ON users (email) NULLS NOT DISTINCT;
```

#### ALTER INDEX
```sql
-- Index modifications
ALTER INDEX idx_users_email RENAME TO idx_users_email_old;
ALTER INDEX idx_users_email SET (fillfactor = 80);
```

### Implementation Challenges

#### Covering Indexes
- Complex dependency tracking
- Storage optimization considerations
- Query planner integration

#### Concurrent Operations
- Lock management during creation
- Online index rebuilding
- Minimal downtime requirements

## Best Practices

### Index Naming

```python
# Good index names
good_names = [
    "idx_users_email",              # Single column
    "idx_users_last_first",         # Multiple columns
    "idx_orders_date_status",       # Composite
    "idx_active_users",             # Partial index
    "idx_users_email_lower",        # Functional index
    "uniq_users_email",             # Unique index
]

# Naming patterns
naming_patterns = {
    "regular": "idx_{table}_{columns}",
    "unique": "uniq_{table}_{columns}",
    "partial": "idx_{table}_{condition}",
    "functional": "idx_{table}_{function}",
}
```

### Index Strategy

```python
# Index creation strategy
strategy = {
    "primary_keys": "Automatic B-tree indexes",
    "foreign_keys": "Usually need indexes for joins",
    "where_clauses": "Index columns in WHERE conditions",
    "order_by": "Index columns in ORDER BY",
    "group_by": "Index columns in GROUP BY",
    "json_queries": "GIN indexes for JSON operations",
    "text_search": "GIN/GiST for full-text search",
}

# Avoid over-indexing
avoid_patterns = {
    "too_many_indexes": "More than 5-10 indexes per table",
    "unused_indexes": "Monitor pg_stat_user_indexes",
    "duplicate_indexes": "Same column combinations",
    "very_wide_indexes": "More than 6 columns",
}
```