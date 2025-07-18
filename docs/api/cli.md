# CLI Interface

pgdelta provides a command-line interface for generating schema diffs and DDL migrations.

## Installation

**Note**: pgdelta is not yet published to PyPI. Install from source:

```bash
git clone https://github.com/olirice/pgdelta.git
cd pgdelta
pip install -e ".[dev]"
```

## Commands

### `pgdelta diff-headless`

Generate a diff between two schemas using isolated Docker containers.

```bash
pgdelta diff-headless [OPTIONS]
```

This command creates temporary PostgreSQL containers, applies the provided SQL to create schemas, and generates the DDL needed to transform one schema to match the other.

#### Options

**`--master-sql TEXT`**
: SQL statements to create the master (target) schema

**`--branch-sql TEXT`**
: SQL statements to create the branch (source) schema

**`--initial-sql TEXT`**
: Optional SQL to run in both databases before applying schema SQL (useful for extensions, custom types, etc.)

**`-i, --postgres-image TEXT`**
: PostgreSQL Docker image to use (default: `postgres:17`)

**`-o, --output PATH`**
: Output file path (default: stdout)

**`--verify / --no-verify`**
: Verify generated SQL with roundtrip test (default: `--verify`)

**`-v, --verbose`**
: Show verbose output

#### Examples

**Basic usage:**
```bash
pgdelta diff-headless \
    --initial-sql "CREATE TABLE users (id SERIAL PRIMARY KEY);" \
    --branch-sql "ALTER TABLE users ADD COLUMN email TEXT;"
```

**With multiple schemas:**
```bash
pgdelta diff-headless \
    --initial-sql "CREATE SCHEMA app; CREATE TABLE app.users (id SERIAL PRIMARY KEY);" \
    --branch-sql "ALTER TABLE app.users ADD COLUMN email TEXT;"
```

**Output to file:**
```bash
pgdelta diff-headless \
    --initial-sql "CREATE SCHEMA app; CREATE TABLE app.users (id SERIAL);" \
    --branch-sql "ALTER TABLE app.users ADD COLUMN email TEXT;" \
    --output migration.sql
```

**Using different PostgreSQL version:**
```bash
pgdelta diff-headless \
    --postgres-image "postgres:16" \
    --initial-sql "CREATE TABLE test (id INTEGER);" \
    --branch-sql "ALTER TABLE test ADD COLUMN name TEXT;"
```

#### Output

The command generates SQL DDL statements that apply the branch changes to the initial schema:

```sql
ALTER TABLE "users" ADD COLUMN "email" text;
```

#### Verification

When `--verify` is enabled (default), pgdelta performs a roundtrip test:

1. Applies the generated SQL to the master database
2. Extracts the resulting schema
3. Compares it with the branch schema
4. Reports success or failure

**Verification success:**
```
✅ Verification passed - generated SQL is correct
```

**Verification failure:**
```
⚠️ Verification failed - generated SQL may not be complete
```

### `pgdelta info`

Display pgdelta and system information.

```bash
pgdelta info
```

Shows:
- pgdelta version
- Python version and implementation
- Operating system details
- System architecture
- Hardware information

#### Example Output

```
🐘 pgdelta Information
┌─────────────────────┬──────────────────────────┐
│ Property            │ Value                    │
├─────────────────────┼──────────────────────────┤
│ Version             │ 0.1.0                    │
│ Python Version      │ 3.13.0 (CPython)        │
│ Python Executable   │ /usr/bin/python3.13      │
└─────────────────────┴──────────────────────────┘

💻 System Information
┌─────────────────────┬──────────────────────────┐
│ Property            │ Value                    │
├─────────────────────┼──────────────────────────┤
│ Operating System    │ Linux 6.2.0             │
│ OS Version          │ Ubuntu 22.04.3 LTS      │
│ Machine Type        │ x86_64                   │
│ Architecture        │ 64bit                    │
│ Processor           │ x86_64                   │
└─────────────────────┴──────────────────────────┘
```

### `pgdelta --version`

Show version information and exit.

```bash
pgdelta --version
```

Output:
```
pgdelta version 0.1.0
```

## Exit Codes

- **0**: Success
- **1**: Error occurred (invalid arguments, SQL errors, verification failures, etc.)

## Dependencies

The CLI requires additional dependencies for container-based diffing:

```bash
pip install pgdelta[dev]
```

This installs:
- `testcontainers` for Docker container management
- `psycopg2-binary` for PostgreSQL connectivity
- `sqlalchemy` for database operations

## Docker Requirements

The `diff-headless` command requires Docker to be installed and running:

```bash
# Check if Docker is available
docker --version

# Ensure Docker daemon is running
docker ps
```

## Common Use Cases

### Schema Migration Generation

**Future Interface (Planned)**: pgdelta will connect directly to two databases and diff their catalogs:

```bash
# Planned interface - not yet implemented
pgdelta diff \
    --source "postgresql://user:pass@prod-host/myapp" \
    --target "postgresql://user:pass@dev-host/myapp" \
    --output migration.sql
```

**Current Workaround**: Use pg_dump followed by diff-headless:

```bash
# Export your schemas to SQL files first
pg_dump --schema-only --no-owner myapp_dev > dev_schema.sql
pg_dump --schema-only --no-owner myapp_prod > prod_schema.sql

# Generate migration
pgdelta diff-headless \
    --master-sql "$(cat prod_schema.sql)" \
    --branch-sql "$(cat dev_schema.sql)" \
    --output migration.sql
```

**Note**: Due to limited entity support (extensions, partitioned tables, etc.), the pg_dump approach may currently fail with complex schemas. The direct database connection interface will handle these limitations better.

### Testing Schema Changes

Verify that your manual migration scripts work correctly:

```bash
# Test if your migration transforms schema A to schema B
pgdelta diff-headless \
    --master-sql "$(cat schema_a.sql)" \
    --branch-sql "$(cat schema_b.sql)" \
    --verify
```

### Automated CI/CD Integration

Use in CI/CD pipelines to validate schema changes:

```bash
#!/bin/bash
# Compare feature branch schema with main branch
pgdelta diff-headless \
    --master-sql "$(cat main_schema.sql)" \
    --branch-sql "$(cat feature_schema.sql)" \
    --verify \
    --output migration.sql

# Exit with error if verification fails
if [ $? -ne 0 ]; then
    echo "Schema migration verification failed"
    exit 1
fi
```

## Troubleshooting

### Docker Issues

**Error: Cannot connect to Docker daemon**
```bash
# Ensure Docker is running
sudo systemctl start docker  # Linux
open -a Docker                # macOS
```

**Error: Image not found**
```bash
# Pull the PostgreSQL image first
docker pull postgres:17
```

### Memory Issues

For large schemas, increase Docker memory limits:

```bash
# Check current Docker settings
docker system info | grep -i memory

# Large schemas may need more memory
docker run --memory=4g postgres:17
```

### SQL Syntax Errors

Ensure your SQL is valid PostgreSQL syntax:

```bash
# Test SQL syntax separately
psql -c "$(cat your_schema.sql)" --dry-run
```

If you get syntax errors, check:
- SQL statement terminators (semicolons)
- Quoted identifiers
- PostgreSQL-specific syntax

### Permission Errors

**Error: Permission denied**
```bash
# Ensure user is in docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```