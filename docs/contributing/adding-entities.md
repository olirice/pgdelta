# Adding New Entity Types

This guide walks through the process of adding support for a new PostgreSQL entity type to pgdelta, using indexes as a comprehensive example.

## Overview

Adding a new entity type to pgdelta involves several steps:

1. **Model Creation**: Define the PostgreSQL object model
2. **Extraction**: Extract objects from PostgreSQL catalogs
3. **Diffing**: Compare objects between catalogs
4. **Change Types**: Define create/drop/alter operations
5. **SQL Generation**: Generate DDL from change objects
6. **Testing**: Comprehensive test coverage
7. **Documentation**: Update entity documentation

## Step-by-Step Guide: Adding Index Support

Let's walk through adding index support to demonstrate the complete process.

### Step 1: Model Creation

Create the PostgreSQL model in `src/pgdelta/model/pg_index.py`:

```python
"""PostgreSQL index model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import text

from .base import BasePgModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class PgIndex(BasePgModel):
    """PostgreSQL index model."""
    
    # Identity fields (uniquely identify the index)
    indexname: str = field(metadata={"tag": "identity"})
    schemaname: str = field(metadata={"tag": "identity"})
    
    # Data fields (index properties)
    tablename: str = field(metadata={"tag": "data"})
    index_definition: str = field(metadata={"tag": "data"})
    is_unique: bool = field(metadata={"tag": "data"})
    is_primary: bool = field(metadata={"tag": "data"})
    is_exclusion: bool = field(metadata={"tag": "data"})
    
    # Internal fields (PostgreSQL internals)
    oid: int = field(metadata={"tag": "internal"})
    
    @property
    def stable_id(self) -> str:
        """Cross-database portable identifier."""
        return f"i:{self.schemaname}.{self.indexname}"
    
    @property
    def table_stable_id(self) -> str:
        """Stable ID of the table this index is on."""
        return f"t:{self.schemaname}.{self.tablename}"


def extract_indexes(session: Session) -> list[PgIndex]:
    """Extract indexes from PostgreSQL."""
    
    # Use PostgreSQL's information_schema and pg_* tables
    query = text("""
        SELECT 
            i.indexname,
            i.schemaname,
            i.tablename,
            pg_get_indexdef(pi.oid) as index_definition,
            pi.indisunique as is_unique,
            pi.indisprimary as is_primary,
            pi.indisexclusion as is_exclusion,
            pi.oid
        FROM pg_indexes i
        JOIN pg_class pc ON pc.relname = i.tablename
        JOIN pg_namespace pn ON pn.nspname = i.schemaname AND pn.oid = pc.relnamespace
        JOIN pg_index pi ON pi.indexrelid = (
            SELECT oid FROM pg_class 
            WHERE relname = i.indexname 
            AND relnamespace = pn.oid
        )
        WHERE i.schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY i.schemaname, i.tablename, i.indexname
    """)
    
    result = session.execute(query)
    indexes = []
    
    for row in result:
        index = PgIndex(
            indexname=row.indexname,
            schemaname=row.schemaname,
            tablename=row.tablename,
            index_definition=row.index_definition,
            is_unique=row.is_unique,
            is_primary=row.is_primary,
            is_exclusion=row.is_exclusion,
            oid=row.oid,
        )
        indexes.append(index)
    
    return indexes
```

**Key Points:**
- Use `@dataclass(frozen=True)` for immutability
- Tag fields with metadata: `identity`, `data`, or `internal`
- Implement `stable_id` property for cross-database identification
- Use PostgreSQL system catalogs for extraction
- Filter out system schemas

### Step 2: Catalog Integration

Update `src/pgdelta/catalog.py` to include indexes:

```python
from .model.pg_index import PgIndex, extract_indexes

@dataclass(frozen=True)
class PgCatalog:
    """Immutable PostgreSQL catalog snapshot."""
    
    # ... existing fields ...
    indexes: dict[str, PgIndex]  # Keyed by stable_id
    # ... rest of fields ...

def extract_catalog(session: Session) -> PgCatalog:
    """Extract complete catalog from PostgreSQL session."""
    
    # Extract all object types
    namespaces = extract_namespaces(session)
    classes = extract_classes(session)
    attributes = extract_attributes(session)
    constraints = extract_constraints(session)
    indexes = extract_indexes(session)  # Add this line
    # ... other extractions ...
    
    return PgCatalog(
        namespaces={ns.stable_id: ns for ns in namespaces},
        classes={cls.stable_id: cls for cls in classes},
        attributes={attr.stable_id: attr for attr in attributes},
        constraints={cons.stable_id: cons for cons in constraints},
        indexes={idx.stable_id: idx for idx in indexes},  # Add this line
        # ... other collections ...
    )
```

### Step 3: Diffing Logic

Create diff logic in `src/pgdelta/diff/orchestrator.py`:

```python
def diff_catalogs(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Generate changes to transform master to branch."""
    changes = []
    
    # ... existing diffs ...
    
    # Add index diffing
    changes.extend(diff_indexes(master.indexes, branch.indexes))
    
    # ... rest of diffs ...
    
    return changes

def diff_indexes(
    master_indexes: dict[str, PgIndex],
    branch_indexes: dict[str, PgIndex],
) -> list[DDL]:
    """Diff indexes between catalogs."""
    changes = []
    
    # Find indexes to create (in branch but not master)
    for stable_id, branch_index in branch_indexes.items():
        if stable_id not in master_indexes:
            changes.append(CreateIndex(
                stable_id=stable_id,
                index=branch_index
            ))
    
    # Find indexes to drop (in master but not branch)
    for stable_id, master_index in master_indexes.items():
        if stable_id not in branch_indexes:
            changes.append(DropIndex(
                stable_id=stable_id,
                index=master_index
            ))
    
    # Find indexes to alter (in both but different)
    for stable_id, master_index in master_indexes.items():
        if stable_id in branch_indexes:
            branch_index = branch_indexes[stable_id]
            if not master_index.semantic_equality(branch_index):
                # For indexes, we typically drop and recreate
                changes.append(DropIndex(
                    stable_id=stable_id,
                    index=master_index
                ))
                changes.append(CreateIndex(
                    stable_id=stable_id,
                    index=branch_index
                ))
    
    return changes
```

### Step 4: Change Types

Create change types in `src/pgdelta/changes/index/`:

#### `src/pgdelta/changes/index/__init__.py`
```python
"""Index change types."""

from .create import CreateIndex
from .drop import DropIndex

__all__ = ["CreateIndex", "DropIndex"]
```

#### `src/pgdelta/changes/index/create.py`
```python
"""Create index change type and SQL generation."""

from dataclasses import dataclass

from ...model.pg_index import PgIndex


@dataclass(frozen=True)
class CreateIndex:
    """Create index change."""
    
    stable_id: str  # i:namespace.index_name
    index: PgIndex


def generate_create_index_sql(change: CreateIndex) -> str:
    """Generate CREATE INDEX SQL from the stored index definition."""
    # PostgreSQL's pg_get_indexdef() returns the complete CREATE INDEX statement
    index_def = change.index.index_definition
    
    # Ensure it ends with a semicolon for consistency
    if not index_def.endswith(";"):
        index_def += ";"
    
    return index_def
```

#### `src/pgdelta/changes/index/drop.py`
```python
"""Drop index change type and SQL generation."""

from dataclasses import dataclass

from ...model.pg_index import PgIndex


@dataclass(frozen=True)
class DropIndex:
    """Drop index change."""
    
    stable_id: str  # i:namespace.index_name
    index: PgIndex


def generate_drop_index_sql(change: DropIndex) -> str:
    """Generate DROP INDEX SQL."""
    quoted_schema = f'"{change.index.schemaname}"'
    quoted_index = f'"{change.index.indexname}"'
    
    return f"DROP INDEX {quoted_schema}.{quoted_index};"
```

### Step 5: SQL Generation Integration

Update `src/pgdelta/changes/dispatcher.py`:

```python
from .index import CreateIndex, DropIndex
from .index.create import generate_create_index_sql
from .index.drop import generate_drop_index_sql

def generate_sql(change: DDL) -> str:
    """Generate SQL for a change object using structural pattern matching."""
    
    match change:
        # ... existing cases ...
        
        case CreateIndex() as create_index:
            return generate_create_index_sql(create_index)
        
        case DropIndex() as drop_index:
            return generate_drop_index_sql(drop_index)
        
        # ... rest of cases ...
        
        case _:
            msg = f"Unsupported change type: {type(change)}"
            raise NotImplementedError(msg)
```

### Step 6: Dependencies

Update dependency tracking in `src/pgdelta/model/pg_depend.py`:

```python
def extract_depends(
    session: Session,
    namespaces: list[PgNamespace],
    classes: list[PgClass],
    constraints: list[PgConstraint],
    indexes: list[PgIndex],  # Add this parameter
    # ... other parameters ...
) -> list[PgDepend]:
    """Extract dependencies from pg_depend."""
    
    # ... existing OID mappings ...
    
    # Map index OIDs (indexes also use pg_class)
    for index in indexes:
        oid_to_stable_id[("pg_class", index.oid)] = index.stable_id
    
    # ... rest of function ...
```

### Step 7: Testing

Create comprehensive tests in `tests/`:

#### Unit Tests: `tests/unit/test_index.py`
```python
"""Unit tests for index functionality."""

import pytest
from pgdelta.model.pg_index import PgIndex
from pgdelta.changes.index import CreateIndex, DropIndex
from pgdelta.changes.index.create import generate_create_index_sql
from pgdelta.changes.index.drop import generate_drop_index_sql


def test_pg_index_stable_id():
    """Test PgIndex stable_id property."""
    index = PgIndex(
        indexname="idx_users_email",
        schemaname="public",
        tablename="users",
        index_definition="CREATE INDEX ...",
        is_unique=False,
        is_primary=False,
        is_exclusion=False,
        oid=12345,
    )
    
    assert index.stable_id == "i:public.idx_users_email"


def test_pg_index_table_stable_id():
    """Test PgIndex table_stable_id property."""
    index = PgIndex(
        indexname="idx_users_email",
        schemaname="public",
        tablename="users",
        index_definition="CREATE INDEX ...",
        is_unique=False,
        is_primary=False,
        is_exclusion=False,
        oid=12345,
    )
    
    assert index.table_stable_id == "t:public.users"


def test_create_index_sql_generation():
    """Test CREATE INDEX SQL generation."""
    index = PgIndex(
        indexname="idx_users_email",
        schemaname="public",
        tablename="users",
        index_definition='CREATE INDEX "idx_users_email" ON "public"."users" ("email")',
        is_unique=False,
        is_primary=False,
        is_exclusion=False,
        oid=12345,
    )
    
    change = CreateIndex(
        stable_id="i:public.idx_users_email",
        index=index
    )
    
    sql = generate_create_index_sql(change)
    assert 'CREATE INDEX "idx_users_email"' in sql
    assert 'ON "public"."users"' in sql
    assert sql.endswith(";")


def test_drop_index_sql_generation():
    """Test DROP INDEX SQL generation."""
    index = PgIndex(
        indexname="idx_users_email",
        schemaname="public",
        tablename="users",
        index_definition='CREATE INDEX "idx_users_email" ON "public"."users" ("email")',
        is_unique=False,
        is_primary=False,
        is_exclusion=False,
        oid=12345,
    )
    
    change = DropIndex(
        stable_id="i:public.idx_users_email",
        index=index
    )
    
    sql = generate_drop_index_sql(change)
    assert sql == 'DROP INDEX "public"."idx_users_email";'
```

#### Integration Tests: `tests/integration/test_index_roundtrip.py`
```python
"""Integration tests for index roundtrip fidelity."""

import pytest
from sqlalchemy import text
from pgdelta.catalog import extract_catalog
from pgdelta.changes.dispatcher import generate_sql


def test_index_creation_roundtrip(postgres_session):
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
    
    # Find the index
    index = None
    for idx in catalog.indexes.values():
        if idx.indexname == "idx_test_email":
            index = idx
            break
    
    assert index is not None
    assert index.tablename == "test_table"
    assert index.schemaname == "public"
    assert not index.is_unique
    assert not index.is_primary


def test_unique_index_roundtrip(postgres_session):
    """Test unique index roundtrip fidelity."""
    # Create table with unique index
    postgres_session.execute(text("""
        CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL
        );
        CREATE UNIQUE INDEX idx_test_email_unique ON test_table (email);
    """))
    postgres_session.commit()
    
    # Extract catalog
    catalog = extract_catalog(postgres_session)
    
    # Find the unique index
    index = None
    for idx in catalog.indexes.values():
        if idx.indexname == "idx_test_email_unique":
            index = idx
            break
    
    assert index is not None
    assert index.is_unique
    assert not index.is_primary


def test_index_diff_and_generation(postgres_session):
    """Test index diff and SQL generation."""
    # Create initial table
    postgres_session.execute(text("""
        CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL
        );
    """))
    postgres_session.commit()
    
    # Extract master catalog
    master_catalog = extract_catalog(postgres_session)
    
    # Add index
    postgres_session.execute(text("""
        CREATE INDEX idx_test_email ON test_table (email);
    """))
    postgres_session.commit()
    
    # Extract branch catalog
    branch_catalog = extract_catalog(postgres_session)
    
    # Generate diff
    changes = master_catalog.diff(branch_catalog)
    
    # Should have one CreateIndex change
    assert len(changes) == 1
    assert isinstance(changes[0], CreateIndex)
    
    # Generate SQL
    sql = generate_sql(changes[0])
    assert "CREATE INDEX" in sql
    assert "idx_test_email" in sql
    assert "test_table" in sql
```

### Step 8: Documentation

Update entity documentation in `docs/entities/indexes.md`:

```markdown
# Indexes

PostgreSQL indexes improve query performance by providing faster data access paths.

## PostgreSQL Specification

### CREATE INDEX Syntax
```sql
CREATE [ UNIQUE ] INDEX [ CONCURRENTLY ] [ [ IF NOT EXISTS ] name ]
ON [ ONLY ] table_name [ USING method ]
( { column_name | ( expression ) } [ ... ] )
[ WHERE predicate ]
```

## pgdelta Support

### ✅ Currently Supported
- CREATE INDEX (regular and unique)
- DROP INDEX
- All index types (B-tree, Hash, GIN, GiST, SP-GiST, BRIN)
- Partial indexes with WHERE clause
- Functional indexes with expressions
- Multi-column indexes

### ❌ Not Yet Supported
- ALTER INDEX operations
- CONCURRENTLY option (not needed for schema migration)

## Usage Examples

### Basic Index Creation
```python
target_sql = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL
);
CREATE INDEX idx_users_email ON users (email);
"""
```

## Implementation Details

### Index Model
```python
@dataclass(frozen=True)
class PgIndex:
    indexname: str
    schemaname: str
    tablename: str
    index_definition: str
    is_unique: bool
    is_primary: bool
    is_exclusion: bool
    oid: int
```

### SQL Generation
```python
def generate_create_index_sql(change: CreateIndex) -> str:
    """Generate CREATE INDEX SQL from stored definition."""
    return change.index.index_definition + ";"
```
```

### Step 9: Update Public API

Update `src/pgdelta/__init__.py` to expose new types:

```python
from .changes.index import CreateIndex, DropIndex

__all__ = [
    # ... existing exports ...
    "CreateIndex",
    "DropIndex",
    # ... rest of exports ...
]
```

## Common Patterns

### 1. Model Design Pattern

```python
@dataclass(frozen=True)
class PgEntity(BasePgModel):
    """Template for new entity models."""
    
    # Identity fields (what makes this object unique)
    name: str = field(metadata={"tag": "identity"})
    schema: str = field(metadata={"tag": "identity"})
    
    # Data fields (object properties that matter for DDL)
    property1: str = field(metadata={"tag": "data"})
    property2: bool = field(metadata={"tag": "data"})
    
    # Internal fields (PostgreSQL implementation details)
    oid: int = field(metadata={"tag": "internal"})
    
    @property
    def stable_id(self) -> str:
        """Cross-database portable identifier."""
        return f"prefix:{self.schema}.{self.name}"
```

### 2. Extraction Pattern

```python
def extract_entities(session: Session) -> list[PgEntity]:
    """Extract entities from PostgreSQL."""
    
    # Use appropriate PostgreSQL system catalogs
    query = text("""
        SELECT 
            entity_name,
            schema_name,
            entity_property1,
            entity_property2,
            entity_oid
        FROM pg_entities e
        JOIN pg_namespace n ON n.oid = e.schema_oid
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
        ORDER BY schema_name, entity_name
    """)
    
    result = session.execute(query)
    entities = []
    
    for row in result:
        entity = PgEntity(
            name=row.entity_name,
            schema=row.schema_name,
            property1=row.entity_property1,
            property2=row.entity_property2,
            oid=row.entity_oid,
        )
        entities.append(entity)
    
    return entities
```

### 3. Diffing Pattern

```python
def diff_entities(
    master_entities: dict[str, PgEntity],
    branch_entities: dict[str, PgEntity],
) -> list[DDL]:
    """Diff entities between catalogs."""
    changes = []
    
    # Create entities that exist in branch but not master
    for stable_id, branch_entity in branch_entities.items():
        if stable_id not in master_entities:
            changes.append(CreateEntity(
                stable_id=stable_id,
                entity=branch_entity
            ))
    
    # Drop entities that exist in master but not branch
    for stable_id, master_entity in master_entities.items():
        if stable_id not in branch_entities:
            changes.append(DropEntity(
                stable_id=stable_id,
                entity=master_entity
            ))
    
    # Alter entities that exist in both but are different
    for stable_id, master_entity in master_entities.items():
        if stable_id in branch_entities:
            branch_entity = branch_entities[stable_id]
            if not master_entity.semantic_equality(branch_entity):
                changes.append(AlterEntity(
                    stable_id=stable_id,
                    old_entity=master_entity,
                    new_entity=branch_entity
                ))
    
    return changes
```

### 4. SQL Generation Pattern

```python
def generate_create_entity_sql(change: CreateEntity) -> str:
    """Generate CREATE ENTITY SQL."""
    quoted_schema = f'"{change.entity.schema}"'
    quoted_name = f'"{change.entity.name}"'
    
    sql_parts = [f"CREATE ENTITY {quoted_schema}.{quoted_name}"]
    
    # Add entity-specific properties
    if change.entity.property1:
        sql_parts.append(f"WITH PROPERTY1 = '{change.entity.property1}'")
    
    if change.entity.property2:
        sql_parts.append("WITH PROPERTY2")
    
    return " ".join(sql_parts) + ";"
```

### 5. Testing Pattern

```python
def test_entity_roundtrip(postgres_session):
    """Test entity roundtrip fidelity."""
    # Create entity
    postgres_session.execute(text("""
        CREATE ENTITY test_entity WITH PROPERTY1 = 'value';
    """))
    postgres_session.commit()
    
    # Extract catalog
    catalog = extract_catalog(postgres_session)
    
    # Verify entity exists
    entity_id = "prefix:public.test_entity"
    assert entity_id in catalog.entities
    
    # Verify properties
    entity = catalog.entities[entity_id]
    assert entity.name == "test_entity"
    assert entity.schema == "public"
    assert entity.property1 == "value"
    assert entity.property2 is True
    
    # Test SQL generation
    changes = empty_catalog.diff(catalog)
    sql = generate_sql(changes[0])
    assert "CREATE ENTITY" in sql
    assert "test_entity" in sql
```

## Best Practices

### 1. Model Design

- **Immutable**: Always use `@dataclass(frozen=True)`
- **Field tagging**: Tag all fields with appropriate metadata
- **Stable IDs**: Use consistent, cross-database identifiers
- **Inheritance**: Extend `BasePgModel` for semantic equality

### 2. Extraction

- **System catalogs**: Use PostgreSQL's system catalogs
- **Schema filtering**: Exclude system schemas
- **Ordering**: Order results for consistent output
- **Error handling**: Handle missing or invalid objects

### 3. Diffing

- **Semantic equality**: Use the model's `semantic_equality` method
- **Change types**: Create appropriate change objects
- **Completeness**: Handle create, drop, and alter operations

### 4. SQL Generation

- **Quoting**: Always quote identifiers
- **Formatting**: Use consistent SQL formatting
- **Completeness**: Generate complete, valid SQL
- **Error handling**: Validate inputs and handle edge cases

### 5. Testing

- **Real PostgreSQL**: Use actual PostgreSQL instances
- **Roundtrip fidelity**: Test extract → diff → generate → apply
- **Edge cases**: Test unusual but valid scenarios
- **Performance**: Test with realistic data volumes

## Troubleshooting

### Common Issues

#### Model Not Found
```python
# Error: Model not imported in catalog
from .model.pg_entity import PgEntity, extract_entities

# Solution: Add to catalog.py imports
```

#### SQL Generation Errors
```python
# Error: Change type not handled in dispatcher
match change:
    case CreateEntity() as create_entity:
        return generate_create_entity_sql(create_entity)

# Solution: Add case to generate_sql() function
```

#### Dependency Issues
```python
# Error: Objects created in wrong order
# Solution: Ensure dependencies are properly tracked in pg_depend.py

# Map entity OIDs
for entity in entities:
    oid_to_stable_id[("pg_entity", entity.oid)] = entity.stable_id
```

### Validation Checklist

- [ ] Model extends `BasePgModel`
- [ ] All fields have appropriate metadata tags
- [ ] `stable_id` property is implemented
- [ ] Extraction function queries system catalogs
- [ ] Catalog integration includes new entity type
- [ ] Diff logic handles create/drop/alter operations
- [ ] Change types are immutable dataclasses
- [ ] SQL generation produces valid DDL
- [ ] Dispatcher handles all change types
- [ ] Dependencies are tracked in pg_depend.py
- [ ] Comprehensive unit tests exist
- [ ] Integration tests with real PostgreSQL
- [ ] Roundtrip fidelity tests pass
- [ ] Documentation is updated
- [ ] Public API exports new types

## Summary

Adding a new entity type to pgdelta requires:

1. **Defining the model** with proper field metadata
2. **Implementing extraction** from PostgreSQL catalogs
3. **Creating diff logic** to detect changes
4. **Defining change types** for operations
5. **Implementing SQL generation** for each operation
6. **Adding dependency tracking** for proper ordering
7. **Writing comprehensive tests** with real PostgreSQL
8. **Updating documentation** and public API

This systematic approach ensures that new entity types integrate seamlessly with pgdelta's architecture while maintaining correctness, performance, and maintainability.