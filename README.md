# pgdelta

[![CI](https://github.com/olirice/pgdelta/workflows/CI/badge.svg)](https://github.com/olirice/pgdelta/actions/workflows/ci.yml)
[![Security](https://github.com/olirice/pgdelta/workflows/Security%20&%20Dependencies/badge.svg)](https://github.com/olirice/pgdelta/actions/workflows/security.yml)
[![Coverage Status](https://coveralls.io/repos/github/olirice/pgdelta/badge.svg?branch=master)](https://coveralls.io/github/olirice/pgdelta?branch=master)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A PostgreSQL schema differ and DDL generator that produces high-fidelity schema migrations.

##  Development Status

**pgdelta is currently in early development

## Feature Support Matrix

### Schemas
- ✅ **CREATE SCHEMA** - Basic schema creation
- ✅ **DROP SCHEMA** - Schema deletion
- ❌ **ALTER SCHEMA** - Schema modifications (planned)
  - ❌ Owner to (planned)
  - 🚫 Rename (drop/replace)

### Tables
- ✅ **CREATE TABLE** - Basic table creation
  - ✅ Column definitions with data types
  - ✅ NOT NULL constraints
  - ✅ DEFAULT expressions
  - ✅ Generated columns (GENERATED ALWAYS AS)
  - ✅ Table inheritance (INHERITS)
  - ✅ Storage parameters (WITH clause)
  - ❌ Column STORAGE/COMPRESSION settings (not planned)
  - ❌ Column COLLATE settings (not planned)
  - ❌ LIKE clause (not planned)
  - ❌ PARTITION BY clause (not planned)
  - 🚫 TABLESPACE clause (not applicable)
  - ❌ TEMPORARY/UNLOGGED tables (not applicable)
- ✅ **DROP TABLE** - Table deletion
- ✅ **ALTER TABLE** - Table modifications (partial)
  - ✅ ADD COLUMN (with NOT NULL, DEFAULT)
  - ✅ DROP COLUMN
  - ✅ ALTER COLUMN TYPE (with USING expression)
  - ✅ ALTER COLUMN SET/DROP DEFAULT
  - ✅ ALTER COLUMN SET/DROP NOT NULL
  - 🚫 Table/column renaming (not planned - uses drop/recreate)
  - 🚫 RENAME TO (not planned - uses drop/recreate)
  - 🚫 SET SCHEMA (not planned - uses drop/recreate)

### Constraints
- ✅ **Primary Keys** - CREATE constraint
- ✅ **Unique Constraints** - CREATE constraint
  - ✅ Multi-column unique constraints
  - ✅ Partial unique constraints (WHERE clause)
- ✅ **Check Constraints** - CREATE constraint
- ✅ **Foreign Keys** - CREATE constraint
  - ✅ Multi-column foreign keys
  - ✅ ON DELETE/UPDATE actions (CASCADE, RESTRICT, SET NULL, SET DEFAULT)
  - ✅ Constraint deferrability options
- ✅ **Exclusion Constraints** - CREATE constraint (basic)
- ✅ **DROP CONSTRAINT** - Constraint deletion
- ❌ **ALTER CONSTRAINT** - Constraint modifications (planned)
- ❌ **VALIDATE CONSTRAINT** - Constraint validation (planned)

### Indexes
- ✅ **CREATE INDEX** - Complete index creation
  - ✅ Unique indexes
  - ✅ Partial indexes (WHERE clause)
  - ✅ Functional indexes (expressions)
  - ✅ Multi-column indexes
  - ✅ All index methods (btree, hash, gin, gist, etc.)
  - ✅ Custom operator classes
  - ✅ ASC/DESC ordering
  - ✅ NULLS FIRST/LAST
  - 🚫 CONCURRENTLY option (not applicable)
- ✅ **DROP INDEX** - Index deletion
- ❌ **ALTER INDEX** - Index modifications (planned)
- 🚫 **REINDEX** - Index rebuilding (not applicable)

### Views
- ✅ **CREATE VIEW** - Basic view creation
  - ✅ Schema-qualified names
  - ✅ View definition (AS query)
  - ❌ RECURSIVE views (planned)
  - ❌ Explicit column names (planned)
  - ❌ WITH CHECK OPTION (planned)
- ✅ **DROP VIEW** - View deletion
- ✅ **CREATE OR REPLACE VIEW** - View replacement
- ❌ **ALTER VIEW** - View modifications (planned)

### Materialized Views
- ✅ **CREATE MATERIALIZED VIEW** - Materialized view creation
- ✅ **DROP MATERIALIZED VIEW** - Materialized view deletion
- ❌ **ALTER MATERIALIZED VIEW** - Materialized view modifications (planned)
- 🚫 **REFRESH MATERIALIZED VIEW** - Not applicable for DDL

### Functions & Procedures
- ✅ **CREATE FUNCTION** - Function creation
- ✅ **CREATE PROCEDURE** - Procedure creation
- ✅ **DROP FUNCTION** - Function deletion
- ✅ **DROP PROCEDURE** - Procedure deletion
- ✅ **CREATE OR REPLACE FUNCTION** - Function replacement
- ❌ **ALTER FUNCTION** - Function modifications (planned)
- ❌ **ALTER PROCEDURE** - Procedure modifications (planned)

### Triggers
- ✅ **CREATE TRIGGER** - Trigger creation
- ✅ **DROP TRIGGER** - Trigger deletion
- ❌ **ALTER TRIGGER** - Trigger modifications (planned)
- ❌ **ENABLE/DISABLE TRIGGER** - (planned)

### Sequences
- ✅ **CREATE SEQUENCE** - Sequence creation
- ✅ **DROP SEQUENCE** - Sequence deletion
- ✅ **ALTER SEQUENCE OWNED BY** - Sequence ownership
- ✅ **ALTER SEQUENCE** - Sequence modifications (planned)

### Types & Domains
- ✅ **CREATE TYPE** - Custom type creation (enums, composites, domains)
- ✅ **DROP TYPE** - Type deletion
- ✅ **CREATE DOMAIN** - Domain creation with base type and constraints
- ✅ **DROP DOMAIN** - Domain deletion
- ✅ **ALTER TYPE** - Type modifications (planned)

### Security & Access Control
- ✅ **Row Level Security** - RLS policies
- ✅ **CREATE POLICY** - Policy creation
- ✅ **DROP POLICY** - Policy deletion
- ✅ **ALTER POLICY** - Policy modifications
- ❌ **CREATE ROLE** - Role creation (planned)
- ❌ **GRANT/REVOKE** - Privilege management (planned)
- ❌ **ALTER DEFAULT PRIVILEGES** - Default privilege management (planned)

### Other Features
- ✅ **Dependency Resolution** - Automatic DDL ordering
- ✅ **Roundtrip Fidelity Verification** - Extract → Diff → Generate → Apply cycles
- ❌ **Comments** - Object comments (planned)
- ❌ **Event Triggers** - Event trigger support (planned)
- ❌ **Extensions** - Extension management (planned)

## Architecture

pgdelta uses a **three-phase approach** designed for correctness and testability:

### Phase 1: Extract
- **SQL-only access**: Database connections used exclusively during extraction
- **Immutable snapshots**: One-time catalog extraction into frozen dataclasses
- **Field metadata**: Distinguishes identity, data, and internal fields for semantic comparison

### Phase 2: Diff
- **Semantic comparison**: Uses field metadata to compare objects based on identity and data fields
- **Change detection**: Identifies create, drop, and alter operations
- **Pure comparison**: No database access, operates on immutable snapshots

### Phase 3: Generate
- **Pure functions**: SQL generation from change objects with no side effects
- **Deterministic output**: Same input always produces identical DDL
- **Type-safe**: Complete mypy coverage with structural pattern matching
- **Dependency resolution**: Constraint-based dependency ordering using NetworkX

### Testing Strategy
- **Roundtrip fidelity**: Generic integration tests that verify `Extract(DB) → Diff → Generate(SQL) → Apply(SQL) → Extract(DB)` produces semantically identical catalogs
- **Real PostgreSQL**: All tests use actual PostgreSQL instances via testcontainers

## Technical Decisions

- **Pure Functions**: All core logic uses pure functions with no side effects
- **Immutable Data**: Extract once, operate on immutable snapshots
- **Dependency Resolution**: Constraint-based dependency ordering using NetworkX
- **Type Safety**: Complete type safety with mypy and structural pattern matching
- **Roundtrip Fidelity**: Generates DDL that recreates schemas exactly

## Installation

**Note**: pgdelta is not yet published to PyPI. Install from source:

```bash
git clone https://github.com/olirice/pgdelta.git
cd pgdelta
pip install -e ".[dev]"
```

## Usage

### Python API

```python
from pgdelta import PgCatalog, generate_sql
from pgdelta.catalog import extract_catalog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Connect to databases
source_engine = create_engine("postgresql://user:pass@localhost/source_db")
target_engine = create_engine("postgresql://user:pass@localhost/target_db")

with Session(source_engine) as source_session, Session(target_engine) as target_session:
    # Extract schemas
    source_catalog = extract_catalog(source_session)
    target_catalog = extract_catalog(target_session)

    # Generate migration from target to source
    changes = target_catalog.diff(source_catalog)

    # Generate SQL statements
    sql_statements = [generate_sql(change) for change in changes]

    for sql in sql_statements:
        print(sql)
```

### Example Output

```sql
CREATE SCHEMA "analytics";
CREATE TABLE "analytics"."user_stats" (
  "user_id" integer,
  "post_count" integer DEFAULT 0,
  "last_login" timestamp without time zone
);
```

## Development Setup

### Prerequisites

- Python 3.13+
- Docker (for running PostgreSQL test containers)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/olirice/pgdelta.git
   cd pgdelta
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in editable mode with development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Running Tests

The project uses pytest with real PostgreSQL databases via testcontainers:

```bash
# Run all tests
pytest

# Run tests in parallel (faster)
pytest -n auto

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only

# Run tests with coverage
pytest --cov=src/pgdelta --cov-report=html

# Run a specific test
pytest tests/unit/test_sql_generation.py::test_create_schema_basic
```

### Development Tools

```bash
# Type checking
mypy src/pgdelta

# Linting and formatting
ruff check
ruff format

# Run all pre-commit hooks
pre-commit run --all-files
```

### Test Requirements

- **Docker**: Required for PostgreSQL test containers
- **PostgreSQL 17**: Automatically managed via testcontainers
- **Real Database Testing**: All tests use real PostgreSQL instances, not mocks

## CI/CD

The project includes comprehensive GitHub Actions workflows:

- **CI Pipeline** (`ci.yml`): Runs pre-commit checks and tests on every push/PR
- **Security Scanning** (`security.yml`): Dependency and security analysis
- **Automated Releases** (`release.yml`): Builds and publishes to PyPI on tag push

All workflows use the latest action versions and follow security best practices with minimal permissions.

## Architecture Details

### Model Design

PostgreSQL catalog models are simplified and optimized for DDL generation:

- **Immutable dataclasses**: All models use `@dataclass(frozen=True)` for immutability
- **Essential fields only**: Only fields necessary for DDL generation are included
- **Stable identifiers**: Cross-database portable identifiers using stable_id (no pg_depend_id required)
- **Type safety**: Complete type annotations with mypy compliance

### Field Metadata System

Uses dataclass field metadata to categorize fields with wrapper functions:
- `identity()`: Fields that identify the object (used in semantic comparison)
- `data()`: Fields that represent object data (used in semantic comparison)
- `internal()`: Fields needed for dependency resolution (ignored in semantic comparison)

The wrapper functions generate the appropriate metadata dictionaries, making field categorization cleaner and more maintainable.

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.
