# Sequences

PostgreSQL sequences generate unique numeric identifiers, commonly used for auto-incrementing primary keys.

## PostgreSQL Specification

### CREATE SEQUENCE Syntax
```sql
CREATE [ TEMPORARY | TEMP ] SEQUENCE [ IF NOT EXISTS ] name
    [ AS data_type ]
    [ INCREMENT [ BY ] increment ]
    [ MINVALUE minvalue | NO MINVALUE ]
    [ MAXVALUE maxvalue | NO MAXVALUE ]
    [ START [ WITH ] start ]
    [ CACHE cache ]
    [ [ NO ] CYCLE ]
    [ OWNED BY { table_name.column_name | NONE } ]
```

**Reference**: [PostgreSQL 17 CREATE SEQUENCE](https://www.postgresql.org/docs/17/sql-createsequence.html)

## pgdelta Support

### ✅ Currently Supported
- CREATE SEQUENCE with all options
- DROP SEQUENCE
- Sequence ownership (OWNED BY)
- All sequence parameters (INCREMENT, MINVALUE, MAXVALUE, START, CACHE, CYCLE)

```sql
CREATE SEQUENCE "public"."users_id_seq" 
AS bigint
INCREMENT BY 1
MINVALUE 1
MAXVALUE 9223372036854775807
START WITH 1
CACHE 1
NO CYCLE;

ALTER SEQUENCE "public"."users_id_seq" OWNED BY "public"."users"."id";
```

### ❌ Not Yet Supported
- ALTER SEQUENCE operations
- Sequence value management

### 🚫 Intentionally Not Supported
- TEMPORARY sequences (not persistent schema objects)
- IF EXISTS/IF NOT EXISTS (pgdelta tracks existence)

## Usage Examples

### Basic Sequence
```python
target_sql = """
CREATE SEQUENCE user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
"""
```

### Sequence with Table
```python
target_sql = """
CREATE SEQUENCE user_id_seq;

CREATE TABLE users (
    id BIGINT DEFAULT nextval('user_id_seq') PRIMARY KEY,
    email TEXT NOT NULL
);

ALTER SEQUENCE user_id_seq OWNED BY users.id;
"""
```

### SERIAL Columns (Auto-generated Sequences)
```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,  -- Creates users_id_seq automatically
    email TEXT NOT NULL
);
"""
# pgdelta handles the auto-generated sequence
```

## Implementation Details

### Sequence Models
```python
@dataclass(frozen=True)
class CreateSequence:
    stable_id: str          # Format: "s:schema.sequence_name"
    namespace: str          # Schema name
    seqname: str           # Sequence name
    sequence_definition: str # Complete sequence definition
    owned_by: str | None    # Table.column ownership
```

### SQL Generation
```python
def generate_create_sequence_sql(change: CreateSequence) -> str:
    """Generate CREATE SEQUENCE SQL."""
    sql_parts = [change.sequence_definition]
    
    # Add ownership if specified
    if change.owned_by:
        quoted_seq = f'"{change.namespace}"."{change.seqname}"'
        sql_parts.append(f"ALTER SEQUENCE {quoted_seq} OWNED BY {change.owned_by};")
    
    return "\n".join(sql_parts)
```

## Sequence Parameters

### Data Types
```sql
-- Integer sequences (default)
CREATE SEQUENCE int_seq AS integer;

-- Bigint sequences (for large ranges)
CREATE SEQUENCE bigint_seq AS bigint;

-- Smallint sequences (for small ranges)
CREATE SEQUENCE smallint_seq AS smallint;
```

### Increment Options
```sql
-- Increment by 1 (default)
CREATE SEQUENCE normal_seq INCREMENT BY 1;

-- Increment by 10
CREATE SEQUENCE skip_seq INCREMENT BY 10;

-- Decrement (negative increment)
CREATE SEQUENCE countdown_seq INCREMENT BY -1 START WITH 1000;
```

### Range Options
```sql
-- Custom range
CREATE SEQUENCE custom_range_seq
    MINVALUE 1000
    MAXVALUE 9999
    START WITH 1000;

-- No limits
CREATE SEQUENCE unlimited_seq
    NO MINVALUE
    NO MAXVALUE;
```

### Caching and Cycling
```sql
-- High performance with caching
CREATE SEQUENCE cached_seq CACHE 100;

-- Cycling sequence
CREATE SEQUENCE cycling_seq
    MINVALUE 1
    MAXVALUE 100
    CYCLE;
```

## Future Enhancements

### Planned Features (v0.2.0)
- ALTER SEQUENCE support
- Sequence value synchronization
- Identity column integration

## Best Practices

### Sequence Naming
```python
# Good sequence names
good_names = [
    "users_id_seq",           # Table + column + seq
    "order_number_seq",       # Business identifier
    "invoice_seq",            # Short and clear
]

# Avoid generic names
avoid_names = [
    "seq1", "sequence",       # Non-descriptive
    "my_seq", "temp_seq",     # Unclear purpose
]
```

### Sequence Design
```python
# Sequence design considerations
design_considerations = {
    "data_type": "Use BIGINT for high-volume tables",
    "increment": "Usually 1, higher for bulk operations",
    "cache": "Higher cache for better performance",
    "cycle": "Rarely needed, consider implications",
    "ownership": "Always set OWNED BY for dependent sequences"
}

# Performance tips
performance_tips = {
    "cache_size": "Increase cache for high-throughput sequences",
    "multiple_sequences": "Use separate sequences for different purposes",
    "avoid_gaps": "Gaps are normal and expected in sequences"
}
```

### Common Patterns
```python
# Standard SERIAL pattern
serial_pattern = """
CREATE TABLE table_name (
    id SERIAL PRIMARY KEY,  -- Auto-creates sequence
    -- other columns
);
"""

# Custom sequence pattern
custom_pattern = """
CREATE SEQUENCE table_name_id_seq
    START WITH 1
    INCREMENT BY 1
    CACHE 1;

CREATE TABLE table_name (
    id BIGINT DEFAULT nextval('table_name_id_seq') PRIMARY KEY,
    -- other columns
);

ALTER SEQUENCE table_name_id_seq OWNED BY table_name.id;
"""
```