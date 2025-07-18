# Architecture

pgdelta is designed around a three-phase architecture that separates concerns and ensures correctness through pure functions and immutable data structures.

## Design Principles

### 1. Pure Functions
All core logic uses pure functions with no side effects:
- **Extract**: Read-only database operations
- **Diff**: Pure comparison functions
- **Generate**: Deterministic SQL generation

### 2. Immutable Data
Once extracted, all data is immutable:
- **Catalogs**: Frozen dataclasses that cannot be modified
- **Models**: Immutable representations of PostgreSQL objects
- **Changes**: Immutable change objects

### 3. Separation of Concerns
Each phase has a single responsibility:
- **Extract**: Database interaction and data marshalling
- **Diff**: Semantic comparison and change detection
- **Generate**: SQL generation and dependency resolution

### 4. Type Safety
Complete type safety throughout the system:
- **mypy**: 100% type coverage
- **Structural pattern matching**: Type-safe dispatch
- **Generics**: Type-safe collections

## Three-Phase Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    pgdelta                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │    Phase 1      │    │    Phase 2      │    │    Phase 3      │            │
│  │    Extract      │───▶│      Diff       │───▶│    Generate     │            │
│  │                 │    │                 │    │                 │            │
│  │ • Database      │    │ • Semantic      │    │ • SQL           │            │
│  │   Connections   │    │   Comparison    │    │   Generation    │            │
│  │ • Catalog       │    │ • Change        │    │ • Dependency    │            │
│  │   Extraction    │    │   Detection     │    │   Resolution    │            │
│  │ • Immutable     │    │ • Pure          │    │ • Pure          │            │
│  │   Snapshots     │    │   Functions     │    │   Functions     │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Phase 1: Extract

### Purpose
Extract PostgreSQL schema information into immutable dataclasses.

### Key Components

#### Catalog Extraction
```python
@dataclass(frozen=True)
class PgCatalog:
    """Immutable PostgreSQL catalog snapshot."""
    
    namespaces: dict[str, PgNamespace]      # Schemas
    classes: dict[str, PgClass]             # Tables, views, etc.
    attributes: dict[str, PgAttribute]      # Columns
    constraints: dict[str, PgConstraint]    # Constraints
    indexes: dict[str, PgIndex]             # Indexes
    sequences: dict[str, PgSequence]        # Sequences
    policies: dict[str, PgPolicy]           # RLS policies
    procedures: dict[str, PgProc]           # Functions
    triggers: dict[str, PgTrigger]          # Triggers
    types: dict[str, PgType]                # Custom types
    depends: list[PgDepend]                 # Dependencies
```

#### Model Simplification
pgdelta uses simplified models that focus only on DDL-relevant information:

```python
# PostgreSQL's pg_class has 30+ fields
# pgdelta's PgClass has 4 fields
@dataclass(frozen=True)
class PgClass:
    oid: int = field(metadata={"tag": "internal"})
    relname: str = field(metadata={"tag": "identity"})
    namespace: str = field(metadata={"tag": "identity"})
    relkind: str = field(metadata={"tag": "data"})
```

### Database Interaction
```python
def extract_catalog(session: Session) -> PgCatalog:
    """Extract complete catalog from PostgreSQL session."""
    
    # Extract all object types in dependency order
    namespaces = extract_namespaces(session)
    classes = extract_classes(session)
    attributes = extract_attributes(session)
    constraints = extract_constraints(session)
    indexes = extract_indexes(session)
    sequences = extract_sequences(session)
    policies = extract_policies(session)
    procedures = extract_procedures(session)
    triggers = extract_triggers(session)
    types = extract_types(session)
    depends = extract_depends(session, ...)
    
    # Build immutable catalog
    return PgCatalog(
        namespaces={ns.stable_id: ns for ns in namespaces},
        classes={cls.stable_id: cls for cls in classes},
        # ... other collections
    )
```

## Phase 2: Diff

### Purpose
Compare two catalogs and generate change objects representing the differences.

### Key Components

#### Semantic Equality
```python
def semantic_equality(self, other: BasePgModel) -> bool:
    """Compare objects based on identity and data fields only."""
    if type(self) != type(other):
        return False
    
    for field in fields(self):
        if field.metadata.get("tag") in ("identity", "data"):
            if getattr(self, field.name) != getattr(other, field.name):
                return False
    
    return True
```

#### Change Detection
```python
def diff_catalogs(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Generate changes to transform master to branch."""
    changes = []
    
    # Diff each object type
    changes.extend(diff_namespaces(master.namespaces, branch.namespaces))
    changes.extend(diff_classes(master.classes, branch.classes))
    changes.extend(diff_attributes(master.attributes, branch.attributes))
    changes.extend(diff_constraints(master.constraints, branch.constraints))
    changes.extend(diff_indexes(master.indexes, branch.indexes))
    # ... other types
    
    return changes
```

#### Change Types
Each object type has corresponding change types:

```python
# Schema changes
@dataclass(frozen=True)
class CreateSchema:
    stable_id: str
    nspname: str

@dataclass(frozen=True)
class DropSchema:
    stable_id: str
    nspname: str

# Table changes
@dataclass(frozen=True)
class CreateTable:
    stable_id: str
    namespace: str
    relname: str
    columns: list[PgAttribute]

@dataclass(frozen=True)
class AlterTable:
    stable_id: str
    namespace: str
    relname: str
    add_columns: list[PgAttribute]
    drop_columns: list[str]
    alter_columns: list[AlterColumn]
```

### Diff Algorithms

#### Object-Level Diffing
```python
def diff_objects(
    master_objects: dict[str, T],
    branch_objects: dict[str, T],
    create_fn: Callable[[T], DDL],
    drop_fn: Callable[[T], DDL],
    alter_fn: Callable[[T, T], DDL | None],
) -> list[DDL]:
    """Generic object diffing algorithm."""
    changes = []
    
    # Find objects to create (in branch but not master)
    for stable_id, branch_obj in branch_objects.items():
        if stable_id not in master_objects:
            changes.append(create_fn(branch_obj))
    
    # Find objects to drop (in master but not branch)
    for stable_id, master_obj in master_objects.items():
        if stable_id not in branch_objects:
            changes.append(drop_fn(master_obj))
    
    # Find objects to alter (in both but different)
    for stable_id, master_obj in master_objects.items():
        if stable_id in branch_objects:
            branch_obj = branch_objects[stable_id]
            if not master_obj.semantic_equality(branch_obj):
                alter_change = alter_fn(master_obj, branch_obj)
                if alter_change:
                    changes.append(alter_change)
    
    return changes
```

#### Field-Level Diffing
```python
def diff_table_columns(
    master_table: PgClass,
    branch_table: PgClass,
    master_catalog: PgCatalog,
    branch_catalog: PgCatalog,
) -> AlterTable | None:
    """Diff table columns to generate ALTER TABLE changes."""
    
    master_columns = master_catalog.get_class_attributes(master_table.stable_id)
    branch_columns = branch_catalog.get_class_attributes(branch_table.stable_id)
    
    # Find columns to add
    add_columns = []
    for branch_col in branch_columns:
        if not any(col.attname == branch_col.attname for col in master_columns):
            add_columns.append(branch_col)
    
    # Find columns to drop
    drop_columns = []
    for master_col in master_columns:
        if not any(col.attname == master_col.attname for col in branch_columns):
            drop_columns.append(master_col.attname)
    
    # Find columns to alter
    alter_columns = []
    for master_col in master_columns:
        for branch_col in branch_columns:
            if master_col.attname == branch_col.attname:
                if not master_col.semantic_equality(branch_col):
                    alter_columns.append(AlterColumn(master_col, branch_col))
    
    # Create ALTER TABLE change if any modifications
    if add_columns or drop_columns or alter_columns:
        return AlterTable(
            stable_id=master_table.stable_id,
            namespace=master_table.namespace,
            relname=master_table.relname,
            add_columns=add_columns,
            drop_columns=drop_columns,
            alter_columns=alter_columns,
        )
    
    return None
```

## Phase 3: Generate

### Purpose
Generate SQL DDL from change objects with proper dependency ordering.

### Key Components

#### SQL Generation
```python
def generate_sql(change: DDL) -> str:
    """Generate SQL for a change object using structural pattern matching."""
    
    match change:
        case CreateSchema() as create_schema:
            return generate_create_schema_sql(create_schema)
        
        case CreateTable() as create_table:
            return generate_create_table_sql(create_table)
        
        case AlterTable() as alter_table:
            return generate_alter_table_sql(alter_table)
        
        case CreateIndex() as create_index:
            return generate_create_index_sql(create_index)
        
        case CreateConstraint() as create_constraint:
            return generate_create_constraint_sql(create_constraint)
        
        case _:
            msg = f"Unsupported change type: {type(change)}"
            raise NotImplementedError(msg)
```

#### Dependency Resolution
See the [Dependency Resolution](dependency-resolution.md) documentation for detailed information.

#### SQL Generation Functions
```python
def generate_create_table_sql(change: CreateTable) -> str:
    """Generate CREATE TABLE SQL."""
    quoted_schema = f'"{change.namespace}"'
    quoted_table = f'"{change.relname}"'
    
    sql_parts = [f"CREATE TABLE {quoted_schema}.{quoted_table} ("]
    
    # Add columns
    column_defs = []
    for col in change.columns:
        col_def = f'  "{col.attname}" {col.formatted_type}'
        
        if col.is_generated:
            col_def += f" GENERATED ALWAYS AS ({col.generated_expression}) STORED"
            if col.attnotnull:
                col_def += " NOT NULL"
        else:
            if col.default_value:
                col_def += f" DEFAULT {col.default_value}"
            if col.attnotnull:
                col_def += " NOT NULL"
        
        column_defs.append(col_def)
    
    sql_parts.append("\n" + ",\n".join(column_defs) + "\n")
    sql_parts.append(")")
    
    return "".join(sql_parts) + ";"
```

## Model Architecture

### Base Model
```python
@dataclass(frozen=True)
class BasePgModel:
    """Base class for all PostgreSQL models."""
    
    def semantic_equality(self, other: BasePgModel) -> bool:
        """Compare objects based on identity and data fields only."""
        if type(self) != type(other):
            return False
        
        for field in fields(self):
            if field.metadata.get("tag") in ("identity", "data"):
                if getattr(self, field.name) != getattr(other, field.name):
                    return False
        
        return True
    
    @property
    def stable_id(self) -> str:
        """Cross-database portable identifier."""
        raise NotImplementedError
```

### Field Metadata System
```python
# Field metadata categories
IDENTITY = {"tag": "identity"}    # Uniquely identifies object
DATA = {"tag": "data"}           # Object data/configuration
INTERNAL = {"tag": "internal"}   # PostgreSQL internal fields

# Example usage
@dataclass(frozen=True)
class PgAttribute:
    # Identity fields (used in semantic comparison)
    attname: str = field(metadata=IDENTITY)
    class_stable_id: str = field(metadata=IDENTITY)
    
    # Data fields (used in semantic comparison)
    type_name: str = field(metadata=DATA)
    attnotnull: bool = field(metadata=DATA)
    default_value: str | None = field(metadata=DATA)
    
    # Internal fields (ignored in semantic comparison)
    oid: int = field(metadata=INTERNAL)
    attnum: int = field(metadata=INTERNAL)
```

### Identifier System
pgdelta uses a dual identifier system:

#### Stable ID
Cross-database portable identifier:
```python
# Format: "type_prefix:namespace.name"
stable_ids = {
    "schema": "s:schema_name",
    "table": "t:schema.table_name",
    "view": "v:schema.view_name",
    "index": "i:schema.index_name",
    "constraint": "c:schema.table.constraint_name",
    "sequence": "S:schema.sequence_name",
    "function": "f:schema.function_name",
    "trigger": "tg:schema.table.trigger_name",
    "type": "typ:schema.type_name",
    "policy": "p:schema.table.policy_name",
}
```

#### pg_depend_id
PostgreSQL internal identifier for dependency tracking:
```python
# Format: "classid.objid.objsubid"
pg_depend_id = f"{classid}.{objid}.{objsubid}"
```

## Directory Structure

```
src/pgdelta/
├── __init__.py                 # Public API
├── catalog.py                  # Catalog extraction and management
├── dependency_resolution.py    # Dependency resolution system
├── exceptions.py               # Custom exceptions
│
├── cli/                        # Command-line interface
│   ├── __init__.py
│   └── main.py
│
├── model/                      # PostgreSQL object models
│   ├── __init__.py
│   ├── base.py                 # Base model class
│   ├── pg_attribute.py         # Column model
│   ├── pg_class.py             # Table/view model
│   ├── pg_constraint.py        # Constraint model
│   ├── pg_depend.py            # Dependency model
│   ├── pg_index.py             # Index model
│   ├── pg_namespace.py         # Schema model
│   ├── pg_policy.py            # Policy model
│   ├── pg_proc.py              # Function model
│   ├── pg_sequence.py          # Sequence model
│   ├── pg_trigger.py           # Trigger model
│   └── pg_type.py              # Type model
│
├── diff/                       # Diff algorithms
│   ├── __init__.py
│   └── orchestrator.py         # Main diffing orchestrator
│
└── changes/                    # Change types and SQL generation
    ├── __init__.py
    ├── dispatcher.py           # SQL generation dispatcher
    │
    ├── schema/                 # Schema changes
    │   ├── __init__.py
    │   ├── create.py
    │   └── drop.py
    │
    ├── table/                  # Table changes
    │   ├── __init__.py
    │   ├── create.py
    │   ├── drop.py
    │   └── alter.py
    │
    ├── index/                  # Index changes
    │   ├── __init__.py
    │   ├── create.py
    │   └── drop.py
    │
    └── [other entity types]/   # Other change types
```

## Testing Architecture

### Test Categories

#### Unit Tests
```python
# Test individual components in isolation
def test_create_table_sql_generation():
    """Test CREATE TABLE SQL generation."""
    change = CreateTable(
        stable_id="t:public.users",
        namespace="public",
        relname="users",
        columns=[
            PgAttribute(attname="id", type_name="integer", attnotnull=True),
            PgAttribute(attname="email", type_name="text", attnotnull=True),
        ]
    )
    
    sql = generate_create_table_sql(change)
    assert "CREATE TABLE \"public\".\"users\"" in sql
    assert "\"id\" integer NOT NULL" in sql
    assert "\"email\" text NOT NULL" in sql
```

#### Integration Tests
```python
# Test full workflows with real PostgreSQL
def test_full_diff_workflow(postgres_session):
    """Test complete extract-diff-generate workflow."""
    # Create initial schema
    postgres_session.execute(text("CREATE TABLE users (id SERIAL PRIMARY KEY)"))
    postgres_session.commit()
    
    # Extract master catalog
    master_catalog = extract_catalog(postgres_session)
    
    # Create target schema
    postgres_session.execute(text("ALTER TABLE users ADD COLUMN email TEXT"))
    postgres_session.commit()
    
    # Extract branch catalog
    branch_catalog = extract_catalog(postgres_session)
    
    # Generate changes
    changes = master_catalog.diff(branch_catalog)
    
    # Verify changes
    assert len(changes) == 1
    assert isinstance(changes[0], AlterTable)
    assert changes[0].add_columns[0].attname == "email"
```

#### Roundtrip Tests
```python
# Test that Extract → Diff → Generate → Apply produces identical schemas
def test_roundtrip_fidelity(postgres_session):
    """Test roundtrip fidelity with complex schema."""
    # Create complex schema
    setup_complex_schema(postgres_session)
    
    # Extract catalog
    original_catalog = extract_catalog(postgres_session)
    
    # Generate recreation changes
    empty_catalog = PgCatalog(...)
    changes = empty_catalog.diff(original_catalog)
    
    # Apply changes to empty database
    apply_changes(changes, empty_postgres_session)
    
    # Extract final catalog
    final_catalog = extract_catalog(empty_postgres_session)
    
    # Verify semantic equality
    assert original_catalog.semantically_equals(final_catalog)
```

### Test Infrastructure

#### Test Containers
```python
# Use testcontainers for real PostgreSQL testing
@pytest.fixture
def postgres_container():
    """PostgreSQL test container."""
    with PostgresContainer("postgres:17") as container:
        yield container

@pytest.fixture
def postgres_session(postgres_container):
    """PostgreSQL session for testing."""
    engine = create_engine(postgres_container.get_connection_url())
    with Session(engine) as session:
        yield session
```

#### Test Data Generation
```python
# Generate test data programmatically
def generate_test_schema(complexity: str = "simple") -> str:
    """Generate test schema SQL."""
    if complexity == "simple":
        return """
        CREATE SCHEMA test;
        CREATE TABLE test.users (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL
        );
        """
    elif complexity == "complex":
        return """
        CREATE SCHEMA app;
        CREATE SEQUENCE app.user_id_seq;
        CREATE TABLE app.users (
            id BIGINT DEFAULT nextval('app.user_id_seq') PRIMARY KEY,
            email TEXT NOT NULL UNIQUE
        );
        CREATE INDEX idx_users_email ON app.users (email);
        CREATE VIEW app.active_users AS 
        SELECT * FROM app.users WHERE email IS NOT NULL;
        """
```

## Performance Considerations

### Query Optimization
- **Batch extraction**: Single queries for each object type
- **Index usage**: Leverage PostgreSQL indexes for fast extraction
- **Minimal data**: Extract only essential fields

### Dependency Resolution
- **Focused analysis**: Only analyze objects relevant to changes
- **Efficient algorithms**: Use NetworkX for graph operations
- **Constraint caching**: Reuse constraint calculations

## Error Handling

### Exception Hierarchy
```python
class PgDeltaError(Exception):
    """Base exception for pgdelta errors."""
    pass

class DependencyResolutionError(PgDeltaError):
    """Error during dependency resolution."""
    pass

class CyclicDependencyError(DependencyResolutionError):
    """Cyclic dependency detected."""
    pass
```

### Error Recovery
```python
def safe_extract_catalog(session: Session) -> PgCatalog:
    """Extract catalog with error recovery."""
    try:
        return extract_catalog(session)
    except Exception as e:
        logger.error(f"Failed to extract catalog: {e}")
        # Try to extract partial catalog
        return extract_partial_catalog(session)
```

## Extension Points

### Adding New Object Types
1. Create model in `model/pg_*.py`
2. Add extraction logic
3. Add diffing logic in `diff/`
4. Add change types in `changes/*/`
5. Add SQL generation functions
6. Add tests

### Custom Change Types
```python
@dataclass(frozen=True)
class CustomChange:
    """Custom change type."""
    stable_id: str
    custom_field: str

def generate_custom_change_sql(change: CustomChange) -> str:
    """Generate SQL for custom change."""
    return f"-- Custom change: {change.custom_field}"
```

### Hooks and Plugins
```python
# Future extension point for plugins
class PgDeltaPlugin:
    """Base class for pgdelta plugins."""
    
    def pre_extract(self, session: Session) -> None:
        """Called before catalog extraction."""
        pass
    
    def post_diff(self, changes: list[DDL]) -> list[DDL]:
        """Called after diff generation."""
        return changes
    
    def pre_generate(self, changes: list[DDL]) -> list[DDL]:
        """Called before SQL generation."""
        return changes
```

## Future Architecture Enhancements

### Streaming Processing
```python
# Future: Stream large catalogs to reduce memory usage
async def stream_catalog_extraction(session: AsyncSession) -> AsyncIterator[BasePgModel]:
    """Stream catalog objects for large databases."""
    async for obj in extract_objects_streaming(session):
        yield obj
```

### Parallel Processing
```python
# Future: Parallelize independent operations
async def parallel_sql_generation(changes: list[DDL]) -> list[str]:
    """Generate SQL in parallel for independent changes."""
    tasks = []
    for change in changes:
        if can_generate_in_parallel(change):
            tasks.append(asyncio.create_task(generate_sql_async(change)))
    
    return await asyncio.gather(*tasks)
```

### Caching Layer
```python
# Future: Cache catalog extractions and diff results
class CachingCatalogExtractor:
    """Catalog extractor with caching."""
    
    def __init__(self, cache_backend: CacheBackend):
        self.cache = cache_backend
    
    def extract_catalog(self, session: Session) -> PgCatalog:
        cache_key = self._compute_cache_key(session)
        cached_catalog = self.cache.get(cache_key)
        
        if cached_catalog:
            return cached_catalog
        
        catalog = extract_catalog(session)
        self.cache.set(cache_key, catalog)
        return catalog
```

## Summary

pgdelta's architecture is designed for:
- **Correctness**: Immutable data and pure functions prevent bugs
- **Performance**: Efficient algorithms and minimal data structures
- **Maintainability**: Clear separation of concerns and type safety
- **Extensibility**: Plugin system and extension points for new features
- **Testability**: Real PostgreSQL testing with comprehensive coverage

The three-phase approach ensures that each component has a single responsibility and can be tested independently, while the immutable data structures prevent the complex state management bugs that plague many migration tools.

## Roundtrip Fidelity

One of pgdelta's key guarantees is roundtrip fidelity:

```
Extract(DB1) → Diff → Generate(SQL) → Apply(SQL, DB2) → Extract(DB2)
```

The final Extract(DB2) should produce a catalog that is semantically identical to the original Extract(DB1).

This ensures that:
- No information is lost during the process
- Generated DDL is complete and accurate
- The tool can be used reliably for production migrations

## Testing Philosophy

pgdelta's testing approach emphasizes real-world accuracy:

### Real PostgreSQL Testing
- All tests use actual PostgreSQL instances via testcontainers
- No mocks or simulated behavior
- Tests verify behavior against real database responses

### Roundtrip Testing
- Generic integration tests verify roundtrip fidelity
- Tests ensure Extract → Diff → Generate → Apply cycles work correctly
- Validates that generated DDL recreates schemas exactly

### Coverage Requirements
- Minimum 85% test coverage required
- All code paths must be tested with real PostgreSQL behavior
- Edge cases are tested with actual database scenarios

This testing approach ensures that pgdelta works correctly with real PostgreSQL databases and handles edge cases properly.