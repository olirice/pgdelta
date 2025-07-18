# Types

PostgreSQL supports custom data types including composite types, enums, domains, and ranges.

## PostgreSQL Specification

### CREATE TYPE Syntax
```sql
-- Composite type
CREATE TYPE name AS (
    [ attribute_name data_type [ COLLATE collation ] [, ... ] ]
);

-- Enum type
CREATE TYPE name AS ENUM (
    [ 'label' [, ... ] ]
);

-- Domain type
CREATE DOMAIN name [ AS ] data_type
    [ COLLATE collation ]
    [ DEFAULT expression ]
    [ constraint [ ... ] ]

-- Range type
CREATE TYPE name AS RANGE (
    SUBTYPE = subtype
    [ , SUBTYPE_OPCLASS = subtype_operator_class ]
    [ , COLLATION = collation ]
    [ , CANONICAL = canonical_function ]
    [ , SUBTYPE_DIFF = subtype_diff_function ]
    [ , MULTIRANGE_TYPE_NAME = multirange_type_name ]
);
```

**Reference**: [PostgreSQL 17 CREATE TYPE](https://www.postgresql.org/docs/17/sql-createtype.html)

## pgdelta Support

### ✅ Currently Supported
- CREATE TYPE for composite types
- CREATE TYPE for enum types
- DROP TYPE
- Basic type dependency tracking

```sql
-- Enum type
CREATE TYPE "public"."user_status" AS ENUM ('active', 'inactive', 'pending');

-- Composite type
CREATE TYPE "public"."address" AS (
    street text,
    city text,
    state text,
    zip_code text
);
```

### ❌ Not Yet Supported
- Domain types
- Range types
- Multirange types
- ALTER TYPE operations

### 🚫 Intentionally Not Supported
- Base types (requires C code)
- Shell types (incomplete types)

## Usage Examples

### Enum Types
```python
target_sql = """
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'pending', 'suspended');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    status user_status DEFAULT 'pending'
);
"""
```

### Composite Types
```python
target_sql = """
CREATE TYPE address AS (
    street TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    home_address address,
    work_address address
);
"""
```

### Domain Types (Planned)
```python
# Not yet supported, but planned
target_sql = """
CREATE DOMAIN email AS TEXT
    CHECK (VALUE ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email_address email NOT NULL
);
"""
```

## Implementation Details

### Type Models
```python
@dataclass(frozen=True)
class CreateType:
    stable_id: str          # Format: "typ:schema.type_name"
    namespace: str          # Schema name
    typname: str           # Type name
    typtype: str           # Type category (e=enum, c=composite)
    type_definition: str   # Complete type definition
```

### SQL Generation
```python
def generate_create_type_sql(change: CreateType) -> str:
    """Generate CREATE TYPE SQL."""
    return change.type_definition + ";"
```

## Type Categories

### Enum Types
```sql
-- Status enum
CREATE TYPE order_status AS ENUM ('pending', 'processing', 'shipped', 'delivered');

-- Priority enum
CREATE TYPE priority AS ENUM ('low', 'medium', 'high', 'urgent');

-- Size enum
CREATE TYPE size AS ENUM ('small', 'medium', 'large', 'extra_large');
```

**Use cases:**
- Status fields with fixed values
- Category classifications
- Priority levels
- Size/grade classifications

### Composite Types
```sql
-- Address composite
CREATE TYPE address AS (
    street TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    country TEXT
);

-- Money composite
CREATE TYPE money AS (
    amount DECIMAL(10,2),
    currency TEXT
);

-- Coordinate composite
CREATE TYPE coordinate AS (
    x DOUBLE PRECISION,
    y DOUBLE PRECISION
);
```

**Use cases:**
- Grouping related fields
- Reusable data structures
- Complex data modeling

## Future Enhancements

### Planned Features (v0.2.0)

#### Domain Types
```sql
CREATE DOMAIN email AS TEXT
    CHECK (VALUE ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE DOMAIN positive_integer AS INTEGER
    CHECK (VALUE > 0);
```

#### Range Types
```sql
CREATE TYPE price_range AS RANGE (
    SUBTYPE = DECIMAL,
    SUBTYPE_OPCLASS = numeric_ops
);

CREATE TYPE date_range AS RANGE (
    SUBTYPE = DATE,
    SUBTYPE_OPCLASS = date_ops
);
```

#### ALTER TYPE Operations
```sql
-- Add enum values
ALTER TYPE user_status ADD VALUE 'archived' AFTER 'inactive';

-- Rename enum values
ALTER TYPE user_status RENAME VALUE 'pending' TO 'awaiting_activation';
```

## Best Practices

### Type Naming
```python
# Good type names
good_names = [
    "user_status",           # Descriptive enum
    "address",               # Clear composite type
    "priority_level",        # Specific enum
    "geographic_point",      # Descriptive composite
]

# Naming patterns
patterns = {
    "enums": "Use singular nouns describing the category",
    "composites": "Use nouns describing the data structure",
    "domains": "Use descriptive names with constraints implied"
}
```

### Type Design
```python
# Enum design guidelines
enum_guidelines = {
    "stable_values": "Avoid frequently changing enum values",
    "logical_order": "Order values logically (e.g., priority levels)",
    "future_expansion": "Consider future values when designing",
    "avoid_numbers": "Use descriptive labels, not numeric codes"
}

# Composite type guidelines
composite_guidelines = {
    "related_fields": "Group truly related fields together",
    "avoid_large_types": "Keep composite types reasonably sized",
    "consider_normalization": "Sometimes separate tables are better",
    "null_handling": "Consider NULL behavior in composite fields"
}
```

### Performance Considerations
```python
# Type performance impact
performance_impact = {
    "enums": "Very efficient, stored as integers internally",
    "composites": "Some overhead compared to separate columns",
    "domains": "Constraint checking on every value",
    "ranges": "Efficient for range queries and operations"
}

# Optimization tips
optimization_tips = {
    "enum_ordering": "Order enum values by frequency of use",
    "composite_indexing": "Index individual fields, not entire composite",
    "domain_constraints": "Keep domain constraints simple and fast"
}
```

### Common Patterns
```python
# Status enum pattern
status_pattern = """
CREATE TYPE entity_status AS ENUM ('active', 'inactive', 'pending', 'archived');

CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    status entity_status DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
"""

# Address composite pattern
address_pattern = """
CREATE TYPE address AS (
    street TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    country TEXT DEFAULT 'USA'
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    billing_address address,
    shipping_address address
);
"""
```