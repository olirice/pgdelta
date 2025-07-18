# Constraints

PostgreSQL constraints ensure data integrity by restricting the values that can be stored in tables.

## PostgreSQL Specification

### Constraint Types

#### PRIMARY KEY
```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name PRIMARY KEY (column_name [, ...]);
```

#### FOREIGN KEY
```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name 
FOREIGN KEY (column_name [, ...]) REFERENCES referenced_table (column_name [, ...])
[ MATCH FULL | MATCH PARTIAL | MATCH SIMPLE ]
[ ON DELETE action ] [ ON UPDATE action ]
[ [ NOT ] DEFERRABLE ] [ INITIALLY DEFERRED | INITIALLY IMMEDIATE ];
```

#### UNIQUE
```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name UNIQUE (column_name [, ...]);
```

#### CHECK
```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name CHECK (expression);
```

#### EXCLUDE
```sql
ALTER TABLE table_name ADD CONSTRAINT constraint_name 
EXCLUDE [ USING method ] ( element WITH operator [, ...] ) 
[ WHERE predicate ];
```

**References**: 
- [PostgreSQL 17 ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html)
- [PostgreSQL 17 CREATE TABLE](https://www.postgresql.org/docs/17/sql-createtable.html)

## pgdelta Support

### ✅ Currently Supported

#### PRIMARY KEY Constraints
- Single column primary keys
- Multi-column composite primary keys
- Automatic index creation

```sql
ALTER TABLE "public"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");
```

#### FOREIGN KEY Constraints
- Single column foreign keys
- Multi-column foreign keys
- ON DELETE/UPDATE actions (CASCADE, RESTRICT, SET NULL, SET DEFAULT)
- Constraint deferrability options

```sql
ALTER TABLE "public"."orders" ADD CONSTRAINT "orders_user_id_fkey" 
FOREIGN KEY ("user_id") REFERENCES "public"."users" ("id") ON DELETE CASCADE;
```

#### UNIQUE Constraints
- Single column unique constraints
- Multi-column unique constraints
- Partial unique constraints with WHERE clause

```sql
ALTER TABLE "public"."users" ADD CONSTRAINT "users_email_key" UNIQUE ("email");
```

#### CHECK Constraints
- Column-level check constraints
- Table-level check constraints
- Complex expressions

```sql
ALTER TABLE "public"."users" ADD CONSTRAINT "users_age_check" CHECK (age >= 0);
```

#### EXCLUSION Constraints
- Basic exclusion constraints
- Custom operator specifications
- Spatial exclusion constraints

```sql
ALTER TABLE "public"."reservations" ADD CONSTRAINT "reservations_overlap_excl" 
EXCLUDE USING gist (room_id WITH =, during WITH &&);
```

#### DROP CONSTRAINT
- Constraint deletion
- Cascade behavior through dependency resolution

```sql
ALTER TABLE "public"."users" DROP CONSTRAINT "users_email_key";
```

### ❌ Not Yet Supported

#### ALTER CONSTRAINT
- Constraint modifications
- Deferrability changes
- Constraint validation

#### Advanced Features
- MATCH FULL/PARTIAL for foreign keys
- Complex exclusion constraint expressions

### 🚫 Intentionally Not Supported

#### Environment-Specific Features
- Constraint timing (some aspects are runtime)
- Performance-related constraint options

## Usage Examples

### Primary Key Constraints

```python
# Single column primary key
target_sql = """
CREATE TABLE users (
    id SERIAL,
    email TEXT
);
ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
"""

# Multi-column primary key
target_sql = """
CREATE TABLE order_items (
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER
);
ALTER TABLE order_items ADD CONSTRAINT order_items_pkey 
PRIMARY KEY (order_id, product_id);
"""
```

### Foreign Key Constraints

```python
# Basic foreign key
target_sql = """
CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT);
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    total DECIMAL(10,2)
);
ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES users (id);
"""

# Foreign key with cascade
target_sql = """
ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;
"""
```

### Unique Constraints

```python
# Single column unique
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT
);
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
"""

# Multi-column unique
target_sql = """
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category TEXT
);
ALTER TABLE products ADD CONSTRAINT products_name_category_key 
UNIQUE (name, category);
"""
```

### Check Constraints

```python
# Simple check constraint
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    age INTEGER
);
ALTER TABLE users ADD CONSTRAINT users_age_check CHECK (age >= 0);
"""

# Complex check constraint
target_sql = """
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    price DECIMAL(10,2),
    discount_price DECIMAL(10,2)
);
ALTER TABLE products ADD CONSTRAINT products_price_check 
CHECK (price >= 0 AND discount_price >= 0 AND discount_price <= price);
"""
```

## Implementation Details

### Constraint Models

```python
@dataclass(frozen=True)
class CreateConstraint:
    stable_id: str              # Format: "c:schema.constraint_name"
    constraint: PgConstraint    # Constraint definition

@dataclass(frozen=True)
class PgConstraint:
    conname: str               # Constraint name
    contype: str               # Constraint type (p, f, u, c, x)
    table_name: str            # Table name
    schema_name: str           # Schema name
    constraint_definition: str # Complete constraint definition
    
    @property
    def constraint_type_name(self) -> str:
        type_map = {
            'p': 'PRIMARY KEY',
            'f': 'FOREIGN KEY', 
            'u': 'UNIQUE',
            'c': 'CHECK',
            'x': 'EXCLUDE'
        }
        return type_map.get(self.contype, 'UNKNOWN')
```

### SQL Generation

```python
def generate_create_constraint_sql(change: CreateConstraint) -> str:
    """Generate ADD CONSTRAINT SQL."""
    constraint = change.constraint
    
    quoted_schema = f'"{constraint.schema_name}"'
    quoted_table = f'"{constraint.table_name}"'
    quoted_constraint = f'"{constraint.conname}"'
    
    return (
        f"ALTER TABLE {quoted_schema}.{quoted_table} "
        f"ADD CONSTRAINT {quoted_constraint} "
        f"{constraint.constraint_definition};"
    )
```

## Constraint Types Detail

### Primary Key Constraints

```sql
-- Single column
ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);

-- Multi-column
ALTER TABLE order_items ADD CONSTRAINT order_items_pkey 
PRIMARY KEY (order_id, product_id);
```

**Characteristics:**
- Automatically creates unique B-tree index
- Implies NOT NULL on all columns
- Only one per table
- Referenced by foreign keys

### Foreign Key Constraints

```sql
-- Basic foreign key
ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES users (id);

-- With actions
ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES users (id) 
ON DELETE CASCADE ON UPDATE RESTRICT;

-- Multi-column
ALTER TABLE order_items ADD CONSTRAINT order_items_product_fkey 
FOREIGN KEY (product_id, variant_id) REFERENCES products (id, variant_id);
```

**Actions:**
- `CASCADE`: Delete/update dependent rows
- `RESTRICT`: Prevent delete/update if dependents exist
- `SET NULL`: Set foreign key to NULL
- `SET DEFAULT`: Set foreign key to default value
- `NO ACTION`: Same as RESTRICT (default)

### Unique Constraints

```sql
-- Single column
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);

-- Multi-column
ALTER TABLE products ADD CONSTRAINT products_name_category_key 
UNIQUE (name, category);

-- Partial unique (via partial unique index)
CREATE UNIQUE INDEX users_active_email_key ON users (email) WHERE is_active = true;
```

**Characteristics:**
- Automatically creates unique B-tree index
- Allows multiple NULL values (unless NOT NULL constraint)
- Can be referenced by foreign keys

### Check Constraints

```sql
-- Simple check
ALTER TABLE users ADD CONSTRAINT users_age_check CHECK (age >= 0);

-- Complex check
ALTER TABLE products ADD CONSTRAINT products_price_check 
CHECK (price >= 0 AND discount_price >= 0 AND discount_price <= price);

-- Check with function
ALTER TABLE users ADD CONSTRAINT users_email_check 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

**Characteristics:**
- Evaluated on INSERT/UPDATE
- Can reference multiple columns
- Can use functions and operators
- NOT NULL is a special case of CHECK

### Exclusion Constraints

```sql
-- Basic exclusion
ALTER TABLE reservations ADD CONSTRAINT reservations_overlap_excl 
EXCLUDE USING gist (room_id WITH =, during WITH &&);

-- With WHERE clause
ALTER TABLE reservations ADD CONSTRAINT reservations_active_overlap_excl 
EXCLUDE USING gist (room_id WITH =, during WITH &&) WHERE (is_active = true);
```

**Characteristics:**
- Prevents overlapping values
- Uses GiST or SP-GiST indexes
- Common for time ranges and geometric data
- Can combine multiple operators

## Testing

### Unit Tests

```python
def test_create_primary_key():
    """Test primary key constraint creation."""
    constraint = PgConstraint(
        conname="users_pkey",
        contype="p",
        table_name="users",
        schema_name="public",
        constraint_definition="PRIMARY KEY (id)"
    )
    
    change = CreateConstraint(
        stable_id="c:public.users_pkey",
        constraint=constraint
    )
    
    sql = generate_create_constraint_sql(change)
    assert 'ALTER TABLE "public"."users"' in sql
    assert 'ADD CONSTRAINT "users_pkey"' in sql
    assert 'PRIMARY KEY (id)' in sql
```

### Integration Tests

```python
def test_foreign_key_roundtrip(postgres_session):
    """Test foreign key constraint roundtrip fidelity."""
    # Create tables and foreign key
    postgres_session.execute(text("""
        CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT);
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            total DECIMAL(10,2)
        );
        ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;
    """))
    postgres_session.commit()
    
    # Extract catalog
    catalog = extract_catalog(postgres_session)
    
    # Find constraint
    constraint = next(c for c in catalog.constraints 
                     if c.conname == "orders_user_id_fkey")
    assert constraint.contype == "f"
    assert "ON DELETE CASCADE" in constraint.constraint_definition
```

## Error Handling

### Common Errors

```python
# Constraint violations
try:
    # Foreign key reference to non-existent table
    sql = """
    ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES nonexistent_table (id);
    """
    # pgdelta validates references during extraction
except Exception as e:
    pass

# Name conflicts
try:
    # Duplicate constraint names
    sql = """
    ALTER TABLE users ADD CONSTRAINT users_check CHECK (age >= 0);
    ALTER TABLE users ADD CONSTRAINT users_check CHECK (email IS NOT NULL);
    """
    # pgdelta tracks constraint names
except Exception as e:
    pass
```

### Validation

```python
def validate_constraint_name(name: str) -> bool:
    """Validate constraint name."""
    # Must be valid identifier
    if not name.replace('_', '').isalnum():
        return False
    
    # Reasonable length
    if len(name) > 63:  # PostgreSQL limit
        return False
    
    return True

def validate_check_expression(expression: str) -> bool:
    """Validate check constraint expression."""
    # No subqueries
    if "SELECT" in expression.upper():
        return False
    
    # Balanced parentheses
    if expression.count("(") != expression.count(")"):
        return False
    
    return True
```

## Future Enhancements

### Planned Features (v0.2.0)

#### ALTER CONSTRAINT
```sql
-- Constraint modifications
ALTER TABLE users ALTER CONSTRAINT users_age_check NOT DEFERRABLE;
ALTER TABLE users RENAME CONSTRAINT old_name TO new_name;
```

#### VALIDATE CONSTRAINT
```sql
-- Validate constraints added as NOT VALID
ALTER TABLE users VALIDATE CONSTRAINT users_age_check;
```

#### Enhanced Foreign Keys
```sql
-- MATCH options
ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES users (id) MATCH FULL;
```

## Best Practices

### Constraint Naming

```python
# Good constraint names
naming_patterns = {
    "primary_key": "{table}_pkey",
    "foreign_key": "{table}_{column}_fkey",
    "unique": "{table}_{column}_key",
    "check": "{table}_{column}_{purpose}_check",
    "exclude": "{table}_{purpose}_excl"
}

# Examples
examples = {
    "users_pkey": "Primary key on users table",
    "orders_user_id_fkey": "Foreign key from orders.user_id to users.id",
    "users_email_key": "Unique constraint on users.email",
    "users_age_positive_check": "Check that age is positive",
    "reservations_overlap_excl": "Exclude overlapping reservations"
}
```

### Performance Considerations

```python
# Constraint performance impact
performance_notes = {
    "primary_key": "Minimal impact, creates efficient index",
    "foreign_key": "Requires index on referenced columns",
    "unique": "Creates index, minimal impact",
    "check": "Evaluated on every INSERT/UPDATE",
    "exclude": "Uses GiST index, moderate impact"
}

# Optimization tips
optimization_tips = {
    "foreign_keys": "Ensure referenced columns are indexed",
    "check_constraints": "Use simple expressions when possible",
    "exclusion_constraints": "Consider partial constraints with WHERE",
    "deferrability": "Use DEFERRABLE for complex transactions"
}
```

### Data Integrity Strategy

```python
# Constraint hierarchy
integrity_levels = {
    "essential": ["NOT NULL", "PRIMARY KEY", "FOREIGN KEY"],
    "important": ["UNIQUE", "CHECK (basic validations)"],
    "optional": ["CHECK (complex business rules)", "EXCLUDE"]
}

# When to use each type
use_cases = {
    "primary_key": "Every table needs a primary key",
    "foreign_key": "Maintain referential integrity",
    "unique": "Prevent duplicate values",
    "check": "Enforce business rules at database level",
    "exclude": "Prevent conflicting reservations/schedules"
}
```