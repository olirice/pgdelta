# Functions

PostgreSQL functions are reusable code blocks that can be called from SQL queries.

## PostgreSQL Specification

### CREATE FUNCTION Syntax
```sql
CREATE [ OR REPLACE ] FUNCTION
    name ( [ [ argmode ] [ argname ] argtype [ { DEFAULT | = } default_expr ] [, ...] ] )
    [ RETURNS rettype
      | RETURNS TABLE ( column_name column_type [, ...] ) ]
  { LANGUAGE lang_name
    | TRANSFORM { FOR TYPE type_name } [, ... ]
    | WINDOW
    | { IMMUTABLE | STABLE | VOLATILE }
    | [ NOT ] LEAKPROOF
    | { CALLED ON NULL INPUT | RETURNS NULL ON NULL INPUT | STRICT }
    | { [ EXTERNAL ] SECURITY INVOKER | [ EXTERNAL ] SECURITY DEFINER }
    | PARALLEL { UNSAFE | RESTRICTED | SAFE }
    | COST execution_cost
    | ROWS result_rows
    | SUPPORT support_function
    | SET configuration_parameter { TO value | = value | FROM CURRENT }
    | AS 'definition'
    | AS 'obj_file', 'link_symbol'
    | sql_body
  } ...
```

**Reference**: [PostgreSQL 17 CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html)

## pgdelta Support

### ✅ Currently Supported (via pg_get_functiondef)
- CREATE FUNCTION with complete definition
- DROP FUNCTION
- CREATE OR REPLACE FUNCTION
- CREATE PROCEDURE
- DROP PROCEDURE
- All function languages (SQL, PL/pgSQL, Python, etc.)
- All parameter modes (IN, OUT, INOUT, VARIADIC)
- All return types including RETURNS TABLE
- All function attributes (IMMUTABLE, STABLE, VOLATILE, etc.)
- Security context (SECURITY DEFINER/INVOKER)
- Cost and row estimates
- Configuration parameter settings
- All PostgreSQL function features

```sql
CREATE FUNCTION "public"."calculate_tax"(amount decimal, rate decimal)
RETURNS decimal
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT amount * rate;
$function$;
```

### ❌ Not Yet Supported
- ALTER FUNCTION operations (planned)
- ALTER PROCEDURE operations (planned)

## Usage Examples

### Basic SQL Function
```python
target_sql = """
CREATE FUNCTION calculate_total(price decimal, tax_rate decimal)
RETURNS decimal
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT price * (1 + tax_rate);
$$;
"""
```

### PL/pgSQL Function
```python
target_sql = """
CREATE FUNCTION get_user_order_count(user_id integer)
RETURNS integer
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    order_count integer;
BEGIN
    SELECT COUNT(*) INTO order_count
    FROM orders
    WHERE orders.user_id = $1;

    RETURN order_count;
END;
$$;
"""
```

### Table-Returning Function
```python
target_sql = """
CREATE FUNCTION get_recent_orders(days_back integer)
RETURNS TABLE(id integer, user_id integer, total decimal)
LANGUAGE sql
STABLE
AS $$
    SELECT id, user_id, total
    FROM orders
    WHERE created_at >= CURRENT_DATE - INTERVAL '1 day' * days_back;
$$;
"""
```

## Implementation Details

### Function Models
```python
@dataclass(frozen=True)
class CreateFunction:
    stable_id: str          # Format: "f:schema.function_name"
    namespace: str          # Schema name
    proname: str           # Function name
    function_definition: str # Complete function definition

@dataclass(frozen=True)
class ReplaceFunction:
    stable_id: str          # Format: "f:schema.function_name"
    namespace: str          # Schema name
    proname: str           # Function name
    function_definition: str # New function definition
```

### SQL Generation
```python
def generate_create_function_sql(change: CreateFunction) -> str:
    """Generate CREATE FUNCTION SQL."""
    # Function definition contains the complete CREATE FUNCTION statement
    return change.function_definition + ";"

def generate_replace_function_sql(change: ReplaceFunction) -> str:
    """Generate CREATE OR REPLACE FUNCTION SQL."""
    # Replace CREATE with CREATE OR REPLACE
    definition = change.function_definition
    if definition.startswith("CREATE FUNCTION"):
        definition = definition.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
    return definition + ";"
```

## Function Types

### SQL Functions
```sql
-- Simple calculation
CREATE FUNCTION add_numbers(a integer, b integer)
RETURNS integer
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT a + b;
$$;
```

### PL/pgSQL Functions
```sql
-- Complex logic with control structures
CREATE FUNCTION fibonacci(n integer)
RETURNS integer
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    a integer := 0;
    b integer := 1;
    temp integer;
BEGIN
    FOR i IN 1..n LOOP
        temp := a + b;
        a := b;
        b := temp;
    END LOOP;
    RETURN a;
END;
$$;
```

### Trigger Functions
```sql
-- Function for trigger use
CREATE FUNCTION update_modified_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.modified_at = NOW();
    RETURN NEW;
END;
$$;
```

## Future Enhancements

### Planned Features (v0.2.0)
- Enhanced function overloading support
- Better parameter type resolution
- Function security context tracking

## Best Practices

### Function Naming
```python
# Good function names
good_names = [
    "calculate_tax",          # Verb + noun
    "get_user_orders",        # Clear action
    "validate_email",         # Descriptive purpose
    "format_currency",        # Transformation function
]

# Function categories
categories = {
    "calculations": "calculate_*, compute_*",
    "queries": "get_*, find_*, search_*",
    "validations": "validate_*, check_*, verify_*",
    "transformations": "format_*, convert_*, transform_*"
}
```

### Performance Considerations
```python
# Function volatility
volatility_levels = {
    "IMMUTABLE": "Same input always produces same output",
    "STABLE": "Output doesn't change within single statement",
    "VOLATILE": "Output can change between calls (default)"
}

# Performance impact
performance_tips = {
    "mark_immutable": "Allows aggressive optimization",
    "use_stable": "For functions reading database state",
    "avoid_volatile": "Only when function has side effects"
}
```
