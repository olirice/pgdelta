# pgdelta

[![CI](https://github.com/olirice/pgdelta/workflows/CI/badge.svg)](https://github.com/olirice/pgdelta/actions/workflows/ci.yml)
[![Security](https://github.com/olirice/pgdelta/workflows/Security%20&%20Dependencies/badge.svg)](https://github.com/olirice/pgdelta/actions/workflows/security.yml)
[![Coverage Status](https://coveralls.io/repos/github/olirice/pgdelta/badge.svg?branch=master)](https://coveralls.io/github/olirice/pgdelta?branch=master)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**A PostgreSQL schema differ and DDL generator that produces high-fidelity schema migrations.**

pgdelta is designed to generate precise, dependency-aware DDL migrations by comparing PostgreSQL schemas. It uses a three-phase approach (Extract → Diff → Generate) to ensure correctness and maintains roundtrip fidelity.

## Key Features

- **High-fidelity migrations**: Generates DDL that recreates schemas exactly
- **Dependency resolution**: Automatic ordering of DDL statements based on PostgreSQL dependencies
- **Roundtrip fidelity**: Extract → Diff → Generate → Apply cycles produce identical schemas
- **Type-safe**: Complete mypy coverage with structural pattern matching
- **Real database testing**: All tests use actual PostgreSQL instances via testcontainers

## Development Status

**pgdelta is currently in early development (v0.1.0).**

The project currently supports basic schema and table operations with comprehensive constraint and index support planned for upcoming releases.

## Quick Start

### Installation

**Note**: pgdelta is not yet published to PyPI. Install from source:

```bash
git clone https://github.com/olirice/pgdelta.git
cd pgdelta
pip install -e ".[dev]"
```

### Basic Usage

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

## Architecture Overview

pgdelta uses a **three-phase approach** designed for correctness and testability:

### Phase 1: Extract
- **SQL-only access**: Database connections used exclusively during extraction
- **Immutable snapshots**: One-time catalog extraction into frozen dataclasses
- **Field metadata**: Distinguishes identity, data, and internal fields for semantic comparison

### Phase 2: Diff
- **Dependency resolution**: Uses NetworkX to determine correct DDL ordering
- **Change type inversion**: Dependencies are inverted based on operation type (CREATE vs DROP)
- **Pure comparison**: No database access, operates on immutable snapshots

### Phase 3: Generate
- **Pure functions**: SQL generation from change objects with no side effects
- **Deterministic output**: Same input always produces identical DDL
- **Type-safe**: Complete mypy coverage with structural pattern matching

## What's Supported

### Currently Supported
- ✅ **Schemas**: CREATE/DROP operations
- ✅ **Tables**: CREATE/DROP/ALTER operations with full column support
- ✅ **Constraints**: Primary keys, unique, foreign keys, check, exclusion constraints
- ✅ **Indexes**: Complete index creation and deletion (all types, partial, functional)
- ✅ **Views**: CREATE/DROP/REPLACE operations
- ✅ **Materialized Views**: CREATE/DROP operations
- ✅ **Functions & Procedures**: Full lifecycle management including CREATE OR REPLACE
- ✅ **Triggers**: CREATE/DROP operations
- ✅ **Sequences**: CREATE/DROP operations with ownership tracking, ALTER SEQUENCE OWNED BY
- ✅ **Types**: Enum, composite, and domain type support (CREATE/DROP)
- ✅ **RLS Policies**: CREATE/DROP/ALTER policy management
- ✅ **Dependency Resolution**: Constraint-based dependency ordering
- ✅ **Roundtrip Fidelity**: Extract → Diff → Generate → Apply verification

### Planned Features
- 🔄 **ALTER operations**: ALTER SEQUENCE, ALTER TYPE, ALTER FUNCTION/PROCEDURE, ALTER TRIGGER
- 🔄 **Schema modifications**: ALTER SCHEMA operations
- 🔄 **View enhancements**: RECURSIVE views, explicit column names, WITH CHECK OPTION
- 🔄 **Trigger management**: ENABLE/DISABLE TRIGGER
- 🔄 **Security features**: CREATE ROLE, GRANT/REVOKE, ALTER DEFAULT PRIVILEGES
- 🔄 **Metadata**: Comments on objects
- 🔄 **Advanced features**: Event triggers, Extensions
- 🔄 **Partitioning**: Table partitioning support

## Next Steps

- [Understand the architecture](architecture.md)
- [Explore the API reference](api/python.md)
- [See supported entities](entities/overview.md)
- [Learn about dependency resolution](dependency-resolution.md)
- [Contribute to the project](contributing/setup.md)

## License

Apache 2.0 - see [LICENSE](https://github.com/olirice/pgdelta/blob/master/LICENSE) file for details.
