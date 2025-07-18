# Policies

PostgreSQL Row Level Security (RLS) policies control which rows users can access in tables.

## PostgreSQL Specification

### CREATE POLICY Syntax
```sql
CREATE POLICY name ON table_name
    [ AS { PERMISSIVE | RESTRICTIVE } ]
    [ FOR { ALL | SELECT | INSERT | UPDATE | DELETE } ]
    [ TO { role_name | PUBLIC | CURRENT_ROLE | CURRENT_USER | SESSION_USER } [, ...] ]
    [ USING ( using_expression ) ]
    [ WITH CHECK ( check_expression ) ]
```

**Reference**: [PostgreSQL 17 CREATE POLICY](https://www.postgresql.org/docs/17/sql-createpolicy.html)

## pgdelta Support

### ✅ Currently Supported
- CREATE POLICY with all options
- DROP POLICY
- ALTER POLICY
- All policy types (PERMISSIVE, RESTRICTIVE)
- All policy commands (SELECT, INSERT, UPDATE, DELETE, ALL)

```sql
CREATE POLICY "users_own_data" ON "public"."users"
    FOR ALL
    TO authenticated
    USING (auth.uid() = id);
```

### ❌ Not Yet Supported
- Complex policy dependency optimization
- Policy inheritance patterns

### 🚫 Intentionally Not Supported
- Role-based security (environment-specific)

## Usage Examples

### Basic Row-Level Security
```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy for users to see their own data
CREATE POLICY users_own_data ON users
    FOR ALL
    TO authenticated
    USING (auth.uid() = id);
"""
```

### Restrictive Policy
```python
target_sql = """
CREATE TABLE sensitive_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    data TEXT
);

ALTER TABLE sensitive_data ENABLE ROW LEVEL SECURITY;

-- Only allow access to active users
CREATE POLICY active_users_only ON sensitive_data
    AS RESTRICTIVE
    FOR ALL
    TO authenticated
    USING (EXISTS (SELECT 1 FROM users WHERE users.id = user_id AND is_active = true));
"""
```

### Command-Specific Policies
```python
target_sql = """
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    author_id INTEGER,
    title TEXT,
    content TEXT,
    published BOOLEAN DEFAULT false
);

ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- Users can read published posts or their own posts
CREATE POLICY posts_select ON posts
    FOR SELECT
    TO authenticated
    USING (published = true OR auth.uid() = author_id);

-- Users can only update their own posts
CREATE POLICY posts_update ON posts
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = author_id);
"""
```

## Implementation Details

### Policy Models
```python
@dataclass(frozen=True)
class CreatePolicy:
    stable_id: str              # Format: "p:schema.table.policy_name"
    namespace: str              # Schema name
    table_name: str             # Table name
    policy_name: str            # Policy name
    policy_definition: str      # Complete policy definition

@dataclass(frozen=True)
class AlterPolicy:
    stable_id: str              # Format: "p:schema.table.policy_name"
    namespace: str              # Schema name
    table_name: str             # Table name
    policy_name: str            # Policy name
    policy_definition: str      # New policy definition
```

### SQL Generation
```python
def generate_create_policy_sql(change: CreatePolicy) -> str:
    """Generate CREATE POLICY SQL."""
    return change.policy_definition + ";"

def generate_alter_policy_sql(change: AlterPolicy) -> str:
    """Generate ALTER POLICY SQL."""
    return change.policy_definition + ";"
```

## Policy Types

### Permissive Policies (Default)
```sql
-- Allow access when condition is true
CREATE POLICY permissive_policy ON table_name
    AS PERMISSIVE
    FOR ALL
    USING (condition);
```

### Restrictive Policies
```sql
-- Restrict access unless condition is true
CREATE POLICY restrictive_policy ON table_name
    AS RESTRICTIVE
    FOR ALL
    USING (condition);
```

## Future Enhancements

### Planned Features (v0.2.0)
- Policy inheritance tracking
- Complex policy dependency resolution
- Policy performance analysis

## Best Practices

### Policy Naming
```python
# Good policy names
good_names = [
    "users_own_data",         # Clear ownership
    "published_posts_read",   # Specific action
    "admin_full_access",      # Role-based
    "active_users_only",      # Status-based
]

# Naming patterns
patterns = {
    "ownership": "entity_own_data",
    "action_based": "entity_action_condition",
    "role_based": "role_access_level",
    "status_based": "condition_only"
}
```

### Security Considerations
```python
# RLS security guidelines
security_guidelines = {
    "enable_rls": "Always enable RLS on sensitive tables",
    "default_deny": "Start with restrictive policies",
    "test_policies": "Test with different user contexts",
    "performance": "Keep policy conditions efficient"
}

# Common patterns
common_patterns = {
    "user_isolation": "Users can only access their own data",
    "role_based": "Different access levels for different roles",
    "status_based": "Access based on record status",
    "time_based": "Access based on time conditions"
}
```