# Dependency Resolution

PostgreSQL objects have complex dependency relationships that must be respected when generating DDL migrations. pgdelta uses a sophisticated constraint-based dependency resolution system to ensure SQL statements are generated in the correct order.

## The Challenge

Consider this PostgreSQL schema:

```sql
-- 1. Create schema
CREATE SCHEMA app;

-- 2. Create sequence  
CREATE SEQUENCE app.user_id_seq;

-- 3. Create table that uses sequence
CREATE TABLE app.users (
    id BIGINT DEFAULT nextval('app.user_id_seq') PRIMARY KEY,
    email TEXT NOT NULL
);

-- 4. Create index on table
CREATE INDEX idx_users_email ON app.users (email);

-- 5. Create view that references table
CREATE VIEW app.active_users AS 
SELECT * FROM app.users WHERE email IS NOT NULL;

-- 6. Set sequence ownership
ALTER SEQUENCE app.user_id_seq OWNED BY app.users.id;
```

When generating DDL to create this schema, the operations must be performed in a specific order:
1. Schema must exist before any objects are created in it
2. Sequence must exist before table references it
3. Table must exist before index is created on it
4. Table must exist before view references it
5. Both sequence and table must exist before setting ownership

**The wrong order will cause PostgreSQL errors!**

## pgdelta's Solution: Constraint-Based Resolution

pgdelta uses a modern constraint-based approach that separates concerns:

1. **Extract Dependencies**: Find all relevant object relationships
2. **Generate Constraints**: Apply semantic rules to create ordering constraints
3. **Solve Constraints**: Use topological sorting to find valid ordering

This approach is more maintainable and extensible than traditional conditional logic.

## Dependency Sources

pgdelta identifies dependencies from multiple sources:

### pg_depend
PostgreSQL's internal dependency tracking system that records explicit dependencies between objects.

### Implicit Dependencies
- **Schema ownership**: Objects must be created in existing schemas
- **Table-column relationships**: Columns belong to tables
- **Index-table relationships**: Indexes are built on tables

### Constraint Dependencies
- **Foreign key references**: Foreign keys depend on referenced tables
- **Check constraint dependencies**: Check constraints may reference other objects

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Master Catalog  │    │ Branch Catalog  │    │ Change List     │
│ (current state) │    │ (target state)  │    │ (operations)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │    DependencyExtractor      │
                  │                             │
                  │ • Finds relevant objects    │
                  │ • Extracts dependencies     │
                  │ • Builds dependency model   │
                  └─────────────────────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │    OperationSemantics       │
                  │                             │
                  │ • Applies semantic rules    │
                  │ • Generates constraints     │
                  │ • Handles special cases     │
                  └─────────────────────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │    ConstraintSolver         │
                  │                             │
                  │ • Builds constraint graph   │
                  │ • Performs topological sort │
                  │ • Returns ordered changes   │
                  └─────────────────────────────┘
```

## Components Deep Dive

### 1. DependencyExtractor

**Purpose**: Extract only the dependencies relevant to the current changeset.

**Key Insight**: Instead of analyzing the entire database, focus only on objects that are being changed or could affect the changes.

```python
class DependencyExtractor:
    """Extracts dependencies relevant to a changeset from catalogs."""
    
    def __init__(self, master_catalog: PgCatalog, branch_catalog: PgCatalog):
        # Store both current state (master) and target state (branch)
        self.master_catalog = master_catalog
        self.branch_catalog = branch_catalog
```

#### Finding Relevant Objects

The extractor uses **transitive discovery** to find all objects that could be relevant:

```python
def _find_relevant_objects(self, changes: list[DDL], max_depth: int = 2) -> set[str]:
    """Find all objects relevant to the changeset using transitive discovery."""
    # Start with objects being directly changed
    relevant = {change.stable_id for change in changes}
    
    # Add transitive dependencies up to max_depth
    for _ in range(max_depth):
        new_objects = set()
        for obj_id in relevant:
            # Add dependencies from both catalogs
            # (objects this object depends on)
            new_objects.update(
                self._get_direct_dependencies(obj_id, self.master_catalog)
            )
            new_objects.update(
                self._get_direct_dependencies(obj_id, self.branch_catalog)
            )
            
            # Add dependents from both catalogs
            # (objects that depend on this object)
            new_objects.update(
                self._get_direct_dependents(obj_id, self.master_catalog)
            )
            new_objects.update(
                self._get_direct_dependents(obj_id, self.branch_catalog)
            )
        
        # Stop if no new objects found
        if not new_objects - relevant:
            break
        relevant.update(new_objects)
    
    return relevant
```

**Why transitive discovery?** If we're creating table A that depends on sequence B, and sequence B depends on schema C, we need to know about all three relationships even if we're only changing table A.

#### Building the Dependency Model

The extractor builds a unified model containing dependencies from both catalogs:

```python
def _extract_from_catalog(
    self,
    model: DependencyModel,
    catalog: PgCatalog,
    relevant_objects: set[str],
    source: str,
) -> None:
    """Extract dependencies from a catalog for relevant objects only."""
    for depend in catalog.depends:
        # Only include dependencies between relevant objects
        if (
            depend.dependent_stable_id in relevant_objects
            and depend.referenced_stable_id in relevant_objects
            and not depend.dependent_stable_id.startswith("unknown.")
            and not depend.referenced_stable_id.startswith("unknown.")
        ):
            # Tag each dependency with its source catalog
            model.add_dependency(
                depend.dependent_stable_id, 
                depend.referenced_stable_id, 
                source  # "master" or "branch"
            )
```

**Why both catalogs?** Dependencies exist in different states:
- **Master catalog**: Shows current dependencies (needed for DROP operations)
- **Branch catalog**: Shows target dependencies (needed for CREATE operations)

### 2. OperationSemantics

**Purpose**: Apply semantic rules to generate ordering constraints between operations.

**Key Insight**: Different operation types (CREATE, DROP, ALTER) have different semantic requirements for dependency ordering.

```python
class OperationSemantics:
    """Defines semantic rules for ordering operations based on dependencies."""
    
    def generate_constraints(
        self, changes: list[DDL], model: DependencyModel
    ) -> list[Constraint]:
        """Generate ordering constraints from changes and dependency model."""
        constraints = []
        
        # Add dependency-based constraints
        # (operations must respect object dependencies)
        constraints.extend(self._generate_dependency_constraints(changes, model))
        
        # Add same-object operation constraints
        # (operations on same object have specific ordering rules)
        constraints.extend(self._generate_same_object_constraints(changes))
        
        return constraints
```

#### Dependency-Based Constraints

The core logic analyzes pairs of operations and determines if they should be ordered:

```python
def _analyze_dependency_constraint(
    self, i: int, change_a: DDL, j: int, change_b: DDL, model: DependencyModel
) -> Constraint | None:
    """Analyze if two changes should be ordered based on dependencies."""
    
    # CRITICAL: Choose appropriate catalog state for each operation
    # For CREATE operations, use branch catalog (where dependencies will exist after creation)
    # For DROP operations, use master catalog (where dependencies exist before deletion)
    source_a = "master" if is_drop_change(change_a) else "branch"
    source_b = "master" if is_drop_change(change_b) else "branch"
    
    # Check for dependencies in appropriate states
    a_depends_on_b = model.has_dependency(
        change_a.stable_id, change_b.stable_id, source_a
    )
    b_depends_on_a = model.has_dependency(
        change_b.stable_id, change_a.stable_id, source_b
    )
    
    # Apply semantic rules based on discovered dependencies
    if a_depends_on_b:
        return self._dependency_semantic_rule(
            i, change_a, j, change_b, "a_depends_on_b"
        )
    elif b_depends_on_a:
        return self._dependency_semantic_rule(
            j, change_b, i, change_a, "b_depends_on_a"
        )
    
    return None
```

**Why different catalog states?** Consider these scenarios:

- **CREATE operations**: Need to look at branch catalog to see what dependencies will exist
- **DROP operations**: Need to look at master catalog to see what dependencies currently exist

#### Semantic Rules

Once a dependency is found, different rules apply based on operation types:

```python
def _dependency_semantic_rule(
    self,
    dep_idx: int,
    dependent_change: DDL,
    ref_idx: int,
    referenced_change: DDL,
    reason: str,
) -> Constraint | None:
    """Apply semantic rules when dependent_change depends on referenced_change."""
    
    # Rule 1: For DROP operations, drop dependents before dependencies
    if is_drop_change(dependent_change) and is_drop_change(referenced_change):
        return Constraint(
            dep_idx,                    # Drop dependent first
            ConstraintType.BEFORE,
            ref_idx,                    # Before dropping dependency
            f"DROP dependent before dependency ({reason})",
        )
    
    # Rule 2: For CREATE operations, create dependencies before dependents
    elif is_create_change(dependent_change) and is_create_change(referenced_change):
        return Constraint(
            ref_idx,                    # Create dependency first
            ConstraintType.BEFORE,
            dep_idx,                    # Before creating dependent
            f"CREATE dependency before dependent ({reason})",
        )
    
    # Rule 3: For mixed operations, ensure dependencies exist first
    elif (
        is_create_change(dependent_change)
        or is_alter_change(dependent_change)
        or is_replace_change(dependent_change)
    ) and (
        is_create_change(referenced_change)
        or is_alter_change(referenced_change)
        or is_replace_change(referenced_change)
    ):
        return Constraint(
            ref_idx,                    # Ensure dependency exists first
            ConstraintType.BEFORE,
            dep_idx,                    # Before creating/altering dependent
            f"Ensure dependency exists before dependent ({reason})",
        )
    
    # Rule 4: DROP before CREATE/ALTER/REPLACE
    elif is_drop_change(referenced_change) and (
        is_create_change(dependent_change)
        or is_alter_change(dependent_change)
        or is_replace_change(dependent_change)
    ):
        return Constraint(
            ref_idx,                    # DROP first
            ConstraintType.BEFORE,
            dep_idx,                    # Before CREATE/ALTER/REPLACE
            f"DROP before CREATE/ALTER/REPLACE ({reason})",
        )
    
    return None
```

#### Special Cases

Some PostgreSQL relationships require special handling:

```python
# Special rule: For CREATE operations with sequences and tables
# PostgreSQL reports sequence ownership (sequence depends on table)
# But for creation, table depends on sequence (table needs sequence to exist first)
if is_create_change(dependent_change) and is_create_change(referenced_change):
    from pgdelta.changes.sequence import CreateSequence
    from pgdelta.changes.table import CreateTable
    
    # If sequence depends on table, invert for CREATE operations
    if isinstance(dependent_change, CreateSequence) and isinstance(
        referenced_change, CreateTable
    ):
        return Constraint(
            dep_idx,  # CreateSequence should come first
            ConstraintType.BEFORE,
            ref_idx,  # Before CreateTable
            f"CREATE sequence before table that uses it ({reason})",
        )
```

**Why this special case?** PostgreSQL's dependency tracking shows that sequences are "owned by" table columns, making the sequence depend on the table. However, for DDL generation, the table needs the sequence to exist first, so we invert this relationship for CREATE operations.

#### Same-Object Constraints

When multiple operations affect the same object, they need specific ordering:

```python
def _generate_same_object_constraints(self, changes: list[DDL]) -> list[Constraint]:
    """Generate constraints for operations on the same object."""
    constraints = []
    
    # Group changes by object
    object_groups = defaultdict(list)
    for i, change in enumerate(changes):
        object_groups[change.stable_id].append(i)
    
    # Add ordering constraints within each group
    for indices in object_groups.values():
        if len(indices) > 1:
            # Sort by operation priority (DROP < CREATE < ALTER < REPLACE)
            sorted_indices = sorted(
                indices, key=lambda i: self._get_operation_priority(changes[i])
            )
            
            # Add sequential constraints
            for k in range(len(sorted_indices) - 1):
                constraints.append(
                    Constraint(
                        sorted_indices[k],
                        ConstraintType.BEFORE,
                        sorted_indices[k + 1],
                        "Same object operation priority",
                    )
                )
    
    return constraints

def _get_operation_priority(self, change: DDL) -> int:
    """Get operation priority (lower = earlier)."""
    if is_drop_change(change):
        return 0    # DROP first
    elif is_create_change(change):
        return 1    # CREATE second
    elif is_alter_change(change):
        return 2    # ALTER third
    elif is_replace_change(change):
        return 3    # REPLACE last
    else:
        return 4
```

### 3. ConstraintSolver

**Purpose**: Solve the ordering constraints to produce a valid sequence of operations.

**Key Insight**: This is a classic topological sorting problem that can be solved efficiently with graph algorithms.

```python
class ConstraintSolver:
    """Solves ordering constraints to produce a valid sequence."""
    
    def solve(self, changes: list[DDL], constraints: list[Constraint]) -> list[DDL]:
        """Solve constraints using topological sorting."""
        # Build constraint graph
        graph = nx.DiGraph()
        
        # Add all changes as nodes
        for i in range(len(changes)):
            graph.add_node(i)
        
        # Add constraint edges
        for constraint in constraints:
            if constraint.constraint_type == ConstraintType.BEFORE:
                # Add directed edge from A to B (A must come before B)
                graph.add_edge(constraint.change_a_index, constraint.change_b_index)
        
        # Topological sort
        try:
            ordered_indices = list(nx.topological_sort(graph))
            return [changes[i] for i in ordered_indices]
        except nx.NetworkXUnfeasible:
            # This indicates a cyclic dependency
            raise CyclicDependencyError(
                "Cyclic dependency detected in change constraints"
            ) from None
```

**Why NetworkX?** NetworkX provides robust graph algorithms including cycle detection and topological sorting, handling edge cases that would be complex to implement manually.

## Dependency Types

pgdelta tracks various types of PostgreSQL dependencies:

### 1. Schema Dependencies

```python
# Schema contains all objects created in it
# Schema must be created before any objects in it
# Schema must be dropped after all objects in it are dropped

# Example dependency:
# PgDepend(
#     dependent_stable_id="t:app.users",      # table depends on schema
#     referenced_stable_id="s:app",           # schema
#     source="branch"
# )
```

### 2. Table-Column Dependencies

```python
# Columns belong to tables
# Table must exist before columns can be added
# Columns must be dropped before table can be dropped

# Example dependency:
# PgDepend(
#     dependent_stable_id="c:app.users.email",  # column depends on table
#     referenced_stable_id="t:app.users",       # table
#     source="branch"
# )
```

### 3. Index Dependencies

```python
# Indexes are created on tables
# Table must exist before index can be created
# Index must be dropped before table can be dropped

# Example dependency:
# PgDepend(
#     dependent_stable_id="i:app.idx_users_email",  # index depends on table
#     referenced_stable_id="t:app.users",           # table
#     source="branch"
# )
```

### 4. Constraint Dependencies

```python
# Constraints are applied to tables
# Foreign key constraints reference other tables
# Tables must exist before constraints can be added

# Example foreign key dependency:
# PgDepend(
#     dependent_stable_id="c:app.orders_user_id_fkey",  # constraint depends on referenced table
#     referenced_stable_id="t:app.users",               # referenced table
#     source="branch"
# )
```

### 5. Sequence Dependencies

```python
# Sequences can be owned by table columns
# For CREATE operations, sequence must exist before table
# For DROP operations, ownership must be removed before dropping

# Example dependency:
# PgDepend(
#     dependent_stable_id="s:app.user_id_seq",  # sequence depends on table (ownership)
#     referenced_stable_id="t:app.users",       # table
#     source="branch"
# )
```

### 6. View Dependencies

```python
# Views reference tables and other views
# Referenced objects must exist before view can be created
# Views must be dropped before referenced objects can be dropped

# Example dependency:
# PgDepend(
#     dependent_stable_id="v:app.active_users",  # view depends on table
#     referenced_stable_id="t:app.users",        # table
#     source="branch"
# )
```

### 7. Function Dependencies

```python
# Functions can reference tables, types, other functions
# Referenced objects must exist before function can be created

# Example dependency:
# PgDepend(
#     dependent_stable_id="f:app.get_user_count",  # function depends on table
#     referenced_stable_id="t:app.users",          # table
#     source="branch"
# )
```

### 8. Trigger Dependencies

```python
# Triggers are attached to tables and call functions
# Table and function must exist before trigger can be created

# Example dependencies:
# PgDepend(
#     dependent_stable_id="tg:app.users.update_modified_time",  # trigger depends on table
#     referenced_stable_id="t:app.users",                       # table
#     source="branch"
# )
# PgDepend(
#     dependent_stable_id="tg:app.users.update_modified_time",  # trigger depends on function
#     referenced_stable_id="f:app.update_modified_time",        # function
#     source="branch"
# )
```

## Catalog State Management

pgdelta maintains two catalog states to handle dependencies correctly:

### Master Catalog (Current State)

```python
# Contains the current database state
# Used for:
# - DROP operations (what dependencies currently exist)
# - Understanding what needs to be removed
# - Validating that objects exist before dropping them

# Example: When dropping a table, we need to know what indexes/constraints
# currently exist on it so we can drop them first
```

### Branch Catalog (Target State)

```python
# Contains the target database state
# Used for:
# - CREATE operations (what dependencies will exist)
# - Understanding what needs to be created
# - Validating that dependencies will be satisfied

# Example: When creating a table, we need to know what schema it will be in
# so we can ensure the schema exists first
```

### Dual-State Dependency Analysis

```python
def _analyze_dependency_constraint(
    self, i: int, change_a: DDL, j: int, change_b: DDL, model: DependencyModel
) -> Constraint | None:
    """Analyze if two changes should be ordered based on dependencies."""
    
    # CRITICAL: Choose appropriate catalog state for each operation
    source_a = "master" if is_drop_change(change_a) else "branch"
    source_b = "master" if is_drop_change(change_b) else "branch"
    
    # Check for dependencies in appropriate states
    a_depends_on_b = model.has_dependency(
        change_a.stable_id, change_b.stable_id, source_a
    )
    b_depends_on_a = model.has_dependency(
        change_b.stable_id, change_a.stable_id, source_b
    )
    
    # Apply semantic rules...
```

**Why this matters?** Consider a scenario where:
1. We're dropping table A (exists in master, not in branch)
2. We're creating table B (doesn't exist in master, exists in branch)
3. Table B depends on table A in the branch

Without dual-state analysis, we might try to drop table A before creating table B, which would fail because table B needs table A to exist when it's created.

## Error Handling

### Cyclic Dependencies

```python
# Cyclic dependencies are detected during topological sorting
try:
    ordered_indices = list(nx.topological_sort(graph))
    return [changes[i] for i in ordered_indices]
except nx.NetworkXUnfeasible:
    raise CyclicDependencyError(
        "Cyclic dependency detected in change constraints"
    ) from None
```

**What causes cyclic dependencies?**
- Circular foreign key references
- Mutual view dependencies
- Complex constraint interdependencies

**How pgdelta handles them:**
1. Detects cycles during topological sort
2. Raises a clear error message
3. Provides debugging information about the cycle

### Missing Dependencies

```python
# Filter out unknown dependencies during extraction
if (
    depend.dependent_stable_id in relevant_objects
    and depend.referenced_stable_id in relevant_objects
    and not depend.dependent_stable_id.startswith("unknown.")
    and not depend.referenced_stable_id.startswith("unknown.")
):
    model.add_dependency(
        depend.dependent_stable_id, 
        depend.referenced_stable_id, 
        source
    )
```

**Unknown dependencies** occur when:
- System objects are referenced but not tracked
- Complex PostgreSQL internals are involved
- Extension objects are not fully catalogued

## Performance Optimizations

### Changeset-Focused Analysis

```python
def extract_for_changeset(self, changes: list[DDL]) -> DependencyModel:
    """Extract only dependencies relevant to the changeset."""
    model = DependencyModel()
    
    # Find all objects relevant to the changeset
    relevant_objects = self._find_relevant_objects(changes)
    
    # Extract dependencies from both catalogs for relevant objects
    self._extract_from_catalog(
        model, self.master_catalog, relevant_objects, "master"
    )
    self._extract_from_catalog(
        model, self.branch_catalog, relevant_objects, "branch"
    )
    
    return model
```

**Why this matters?** A full PostgreSQL catalog can contain thousands of objects. By focusing only on objects relevant to the current changeset, we:
- Improve performance
- Avoid unnecessary complexity

### Efficient Graph Algorithms

```python
# Use NetworkX for robust graph algorithms
import networkx as nx

# NetworkX provides:
# - Efficient topological sorting
# - Cycle detection
# - Graph traversal algorithms
# - Well-tested implementations
```

### Dependency Indexing

```python
class DependencyModel:
    def __init__(self) -> None:
        self.dependencies: set[ObjectDependency] = set()
        # Build indexes for fast lookup
        self._dependency_index: dict[str, set[str]] = defaultdict(set)
        self._reverse_index: dict[str, set[str]] = defaultdict(set)
    
    def add_dependency(self, dependent: str, referenced: str, source: str = "") -> None:
        """Add a dependency between objects."""
        dep = ObjectDependency(dependent, referenced, source)
        if dep not in self.dependencies:
            self.dependencies.add(dep)
            # Update indexes for O(1) lookup
            self._dependency_index[dependent].add(referenced)
            self._reverse_index[referenced].add(dependent)
```

## Testing and Validation

### Unit Tests

pgdelta includes comprehensive unit tests for dependency resolution:

```python
def test_create_sequence_before_table():
    """Test that sequences are created before tables that use them."""
    changes = [
        CreateTable(stable_id="t:app.users", ...),
        CreateSequence(stable_id="s:app.user_id_seq", ...),
    ]
    
    # Build dependency model
    model = DependencyModel()
    model.add_dependency("t:app.users", "s:app.user_id_seq", "branch")
    
    # Resolve dependencies
    resolver = DependencyResolver(master_catalog, branch_catalog)
    ordered_changes = resolver.resolve_dependencies(changes)
    
    # Verify sequence comes before table
    assert ordered_changes[0].stable_id == "s:app.user_id_seq"
    assert ordered_changes[1].stable_id == "t:app.users"
```

### Integration Tests

```python
def test_complex_schema_dependencies():
    """Test dependency resolution with complex real-world schema."""
    # Create complex schema with multiple interdependencies
    sql = """
    CREATE SCHEMA app;
    CREATE SEQUENCE app.user_id_seq;
    CREATE TABLE app.users (
        id BIGINT DEFAULT nextval('app.user_id_seq') PRIMARY KEY,
        email TEXT NOT NULL
    );
    CREATE INDEX idx_users_email ON app.users (email);
    CREATE VIEW app.active_users AS 
    SELECT * FROM app.users WHERE email IS NOT NULL;
    ALTER SEQUENCE app.user_id_seq OWNED BY app.users.id;
    """
    
    # Generate changes
    changes = generate_changes_from_sql(sql)
    
    # Resolve dependencies
    ordered_changes = resolve_dependencies(changes, master_catalog, branch_catalog)
    
    # Verify correct ordering
    assert_schema_created_first(ordered_changes)
    assert_sequence_created_before_table(ordered_changes)
    assert_table_created_before_index(ordered_changes)
    assert_table_created_before_view(ordered_changes)
```

### Roundtrip Fidelity Tests

```python
def test_dependency_roundtrip_fidelity():
    """Test that dependency resolution maintains roundtrip fidelity."""
    # Extract catalog from database
    original_catalog = extract_catalog(session)
    
    # Generate changes to recreate schema
    changes = generate_recreation_changes(original_catalog)
    
    # Resolve dependencies
    ordered_changes = resolve_dependencies(changes, empty_catalog, original_catalog)
    
    # Apply changes to empty database
    apply_changes(ordered_changes, empty_session)
    
    # Extract new catalog
    new_catalog = extract_catalog(empty_session)
    
    # Verify catalogs are semantically identical
    assert original_catalog.semantically_equals(new_catalog)
```

## Debugging Dependency Issues

### Constraint Visualization

```python
def debug_constraints(changes: list[DDL], constraints: list[Constraint]):
    """Debug constraint generation."""
    print("Generated Constraints:")
    for constraint in constraints:
        change_a = changes[constraint.change_a_index]
        change_b = changes[constraint.change_b_index]
        print(f"  {change_a.stable_id} {constraint.constraint_type.value} {change_b.stable_id}")
        print(f"    Reason: {constraint.reason}")
```

### Dependency Graph Export

```python
def export_dependency_graph(model: DependencyModel, filename: str):
    """Export dependency graph for visualization."""
    graph = nx.DiGraph()
    
    for dep in model.dependencies:
        graph.add_edge(dep.referenced, dep.dependent, source=dep.source)
    
    nx.write_graphml(graph, filename)
    # Open in graph visualization tool like Gephi or yEd
```

### Error Diagnosis

```python
def diagnose_cyclic_dependency(changes: list[DDL], constraints: list[Constraint]):
    """Diagnose cyclic dependency errors."""
    graph = nx.DiGraph()
    
    for i in range(len(changes)):
        graph.add_node(i)
    
    for constraint in constraints:
        graph.add_edge(constraint.change_a_index, constraint.change_b_index)
    
    try:
        cycles = list(nx.simple_cycles(graph))
        print(f"Found {len(cycles)} cycles:")
        for cycle in cycles:
            print("  Cycle:")
            for i in cycle:
                print(f"    {changes[i].stable_id}")
    except nx.NetworkXNoCycle:
        print("No cycles found")
```

## Future Enhancements

### Parallel Execution

```python
# Future: Identify operations that can be executed in parallel
def identify_parallel_operations(ordered_changes: list[DDL]) -> list[list[DDL]]:
    """Identify operations that can be executed in parallel."""
    # Operations with no dependencies between them can run in parallel
    # This could significantly improve migration performance
    pass
```

### Dependency Optimization

```python
# Future: Optimize dependency extraction for very large schemas
def optimize_dependency_extraction(changes: list[DDL]) -> set[str]:
    """Optimize dependency extraction for large schemas."""
    # Use more sophisticated algorithms to minimize dependency analysis
    # Consider dependency caching and incremental analysis
    pass
```

### Smart Batching

```python
# Future: Batch related operations for better performance
def batch_related_operations(ordered_changes: list[DDL]) -> list[list[DDL]]:
    """Batch related operations for better performance."""
    # Group operations that can be executed together
    # For example, multiple column additions on the same table
    pass
```

## Best Practices

### 1. Design for Dependency Resolution

When designing PostgreSQL schemas:

```python
# Good: Clear dependency hierarchy
CREATE SCHEMA app;
CREATE SEQUENCE app.user_id_seq;
CREATE TABLE app.users (id BIGINT DEFAULT nextval('app.user_id_seq'));

# Avoid: Circular dependencies
CREATE TABLE app.users (friend_id BIGINT REFERENCES app.users(id));
CREATE TABLE app.friends (user_id BIGINT REFERENCES app.users(id));
```

### 2. Test Complex Dependencies

```python
# Test dependency resolution with complex scenarios
def test_complex_foreign_key_dependencies():
    """Test complex foreign key dependency scenarios."""
    # Create scenario with multiple interdependent tables
    # Verify correct ordering
    pass
```

### 3. Monitor Performance

```python
# Monitor dependency resolution performance
def monitor_dependency_resolution_performance():
    """Monitor dependency resolution performance."""
    start_time = time.time()
    ordered_changes = resolve_dependencies(changes, master_catalog, branch_catalog)
    end_time = time.time()
    
    print(f"Resolved {len(changes)} changes in {end_time - start_time:.2f} seconds")
    print(f"Found {len(ordered_changes)} ordered operations")
```

## Summary

pgdelta's dependency resolution system ensures that DDL migrations are generated in the correct order by:

1. **Extracting relevant dependencies** from both current and target database states
2. **Applying semantic rules** to generate ordering constraints between operations
3. **Solving constraints** using proven graph algorithms to produce valid operation sequences

This approach is:
- **Correct**: Handles complex PostgreSQL dependency scenarios
- **Efficient**: Focuses only on relevant objects and uses optimized algorithms
- **Maintainable**: Separates concerns and uses clear abstractions
- **Extensible**: New operation types only require additional semantic rules

The system has been tested with complex real-world schemas and maintains pgdelta's core guarantee of roundtrip fidelity while ensuring all generated DDL can be applied successfully to PostgreSQL databases.