# Triggers

PostgreSQL triggers are special functions that automatically execute in response to database events.

## PostgreSQL Specification

### CREATE TRIGGER Syntax
```sql
CREATE [ OR REPLACE ] [ CONSTRAINT ] TRIGGER name { BEFORE | AFTER | INSTEAD OF } { event [ OR ... ] }
    ON table_name
    [ FROM referenced_table_name ]
    [ NOT DEFERRABLE | [ DEFERRABLE ] [ INITIALLY IMMEDIATE | INITIALLY DEFERRED ] ]
    [ REFERENCING { { OLD | NEW } TABLE [ AS ] transition_relation_name } [ ... ] ]
    [ FOR [ EACH ] { ROW | STATEMENT } ]
    [ WHEN ( condition ) ]
    EXECUTE { FUNCTION | PROCEDURE } function_name ( arguments )
```

**Reference**: [PostgreSQL 17 CREATE TRIGGER](https://www.postgresql.org/docs/17/sql-createtrigger.html)

## pgdelta Support

### ✅ Currently Supported
- CREATE TRIGGER with complete definition
- DROP TRIGGER
- All trigger types (BEFORE, AFTER, INSTEAD OF)
- All trigger events (INSERT, UPDATE, DELETE, TRUNCATE)
- Row-level and statement-level triggers

```sql
CREATE TRIGGER "update_user_modified_time"
BEFORE UPDATE ON "public"."users"
FOR EACH ROW
EXECUTE FUNCTION update_modified_time();
```

### ❌ Not Yet Supported
- CONSTRAINT triggers
- Transition tables (REFERENCING clause)
- Complex trigger dependency optimization

### 🚫 Intentionally Not Supported
- ENABLE/DISABLE TRIGGER (runtime operation)

## Usage Examples

### Basic Update Trigger
```python
target_sql = """
CREATE FUNCTION update_modified_time()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.modified_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    modified_at TIMESTAMP
);

CREATE TRIGGER update_user_modified_time
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_modified_time();
"""
```

### Audit Trigger
```python
target_sql = """
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT,
    operation TEXT,
    old_values JSON,
    new_values JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE FUNCTION audit_changes()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO audit_log (table_name, operation, old_values, new_values)
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP = 'INSERT' THEN row_to_json(NEW) ELSE NULL END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER audit_users_changes
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION audit_changes();
"""
```

## Implementation Details

### Trigger Models
```python
@dataclass(frozen=True)
class CreateTrigger:
    stable_id: str              # Format: "t:schema.trigger_name"
    namespace: str              # Schema name
    tgname: str                 # Trigger name
    table_name: str             # Table name
    trigger_definition: str     # Complete trigger definition
```

### SQL Generation
```python
def generate_create_trigger_sql(change: CreateTrigger) -> str:
    """Generate CREATE TRIGGER SQL."""
    return change.trigger_definition + ";"
```

## Trigger Types

### Row-Level Triggers
```sql
-- Execute for each affected row
CREATE TRIGGER row_trigger
BEFORE INSERT ON table_name
FOR EACH ROW
EXECUTE FUNCTION trigger_function();
```

### Statement-Level Triggers
```sql
-- Execute once per statement
CREATE TRIGGER statement_trigger
AFTER DELETE ON table_name
FOR EACH STATEMENT
EXECUTE FUNCTION trigger_function();
```

### INSTEAD OF Triggers
```sql
-- For views (make them updatable)
CREATE TRIGGER view_insert_trigger
INSTEAD OF INSERT ON view_name
FOR EACH ROW
EXECUTE FUNCTION handle_view_insert();
```

## Future Enhancements

### Planned Features (v0.2.0)
- CONSTRAINT triggers
- Transition tables support
- Better trigger dependency tracking

## Best Practices

### Trigger Naming
```python
# Good trigger names
good_names = [
    "update_modified_time",       # Action-based
    "audit_changes",              # Purpose-based
    "validate_email_format",      # Validation triggers
    "sync_derived_fields",        # Synchronization triggers
]

# Naming patterns
patterns = {
    "before_triggers": "validate_*, check_*, update_*",
    "after_triggers": "audit_*, log_*, sync_*",
    "instead_of": "handle_*, process_*"
}
```

### Performance Considerations
```python
# Trigger performance impact
performance_impact = {
    "row_triggers": "Execute for each affected row",
    "statement_triggers": "Execute once per statement",
    "complex_logic": "Can significantly impact INSERT/UPDATE performance",
    "cascading_triggers": "Avoid triggers that fire other triggers"
}

# Optimization tips
optimization_tips = {
    "use_when_clause": "Limit trigger execution with WHEN conditions",
    "minimize_work": "Keep trigger functions lightweight",
    "avoid_exceptions": "Exceptions in triggers are expensive",
    "consider_alternatives": "Sometimes application logic is better"
}
```
