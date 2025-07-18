"""
Generic Constraint-Based Dependency Resolution (V5)

This module implements a clean, generic dependency resolver using constraint-based
architecture. It extracts only changeset-relevant dependencies and uses semantic
rules to generate ordering constraints, avoiding the conditional explosion of V1.

Design Principles:
- Changeset-focused: Only analyze dependencies relevant to changes
- Constraint-based: Generate constraints from semantic rules
- Generic: New operations require semantic rules, not conditional logic
- Separation of concerns: Dependency extraction, semantics, and solving are separate
"""

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

import networkx as nx

from .catalog import PgCatalog
from .changes.dispatcher import (
    DDL,
    is_alter_change,
    is_create_change,
    is_drop_change,
    is_replace_change,
)
from .exceptions import CyclicDependencyError


class ConstraintType(Enum):
    """Types of ordering constraints between changes."""

    BEFORE = "before"  # A must happen before B


@dataclass(frozen=True)
class Constraint:
    """Represents an ordering constraint between two changes."""

    change_a_index: int
    constraint_type: ConstraintType
    change_b_index: int
    reason: str = ""

    def __str__(self) -> str:
        return f"Change[{self.change_a_index}] {self.constraint_type.value} Change[{self.change_b_index}]: {self.reason}"


@dataclass(frozen=True)
class ObjectDependency:
    """Represents a dependency between two objects."""

    dependent: str
    referenced: str
    source: str = ""  # Which catalog this dependency comes from

    def __str__(self) -> str:
        return f"{self.dependent} → {self.referenced} ({self.source})"


class DependencyModel:
    """
    Unified model containing both master and branch state dependencies.

    This maintains the dual-graph concept from V1 but in a cleaner abstraction.
    Each dependency is tagged with its source (master_catalog or branch_catalog)
    to enable state-specific analysis.
    """

    def __init__(self) -> None:
        self.dependencies: set[ObjectDependency] = set()
        self._dependency_index: dict[str, set[str]] = defaultdict(set)
        self._reverse_index: dict[str, set[str]] = defaultdict(set)

    def add_dependency(self, dependent: str, referenced: str, source: str = "") -> None:
        """Add a dependency between objects."""
        dep = ObjectDependency(dependent, referenced, source)
        if dep not in self.dependencies:
            self.dependencies.add(dep)
            self._dependency_index[dependent].add(referenced)
            self._reverse_index[referenced].add(dependent)

    def get_dependencies(
        self, obj_id: str, source_filter: str | None = None
    ) -> set[str]:
        """Get objects that obj_id depends on, optionally filtered by source."""
        if source_filter:
            return {
                dep.referenced
                for dep in self.dependencies
                if dep.dependent == obj_id and dep.source == source_filter
            }
        return self._dependency_index[obj_id].copy()

    def get_dependents(self, obj_id: str, source_filter: str | None = None) -> set[str]:
        """Get objects that depend on obj_id, optionally filtered by source."""
        if source_filter:
            return {
                dep.dependent
                for dep in self.dependencies
                if dep.referenced == obj_id and dep.source == source_filter
            }
        return self._reverse_index[obj_id].copy()

    def has_dependency(
        self, dependent: str, referenced: str, source_filter: str | None = None
    ) -> bool:
        """Check if dependent depends on referenced."""
        for dep in self.dependencies:
            if (
                dep.dependent == dependent
                and dep.referenced == referenced
                and (source_filter is None or dep.source == source_filter)
            ):
                return True
        return False


class DependencyExtractor:
    """Extracts dependencies relevant to a changeset from catalogs."""

    def __init__(self, master_catalog: PgCatalog, branch_catalog: PgCatalog):
        self.master_catalog = master_catalog
        self.branch_catalog = branch_catalog

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

    def _find_relevant_objects(
        self, changes: list[DDL], max_depth: int = 2
    ) -> set[str]:
        """Find all objects relevant to the changeset using transitive discovery."""
        relevant = {change.stable_id for change in changes}

        # Add transitive dependencies up to max_depth
        for _ in range(max_depth):
            new_objects = set()
            for obj_id in relevant:
                # Add dependencies from both catalogs
                new_objects.update(
                    self._get_direct_dependencies(obj_id, self.master_catalog)
                )
                new_objects.update(
                    self._get_direct_dependencies(obj_id, self.branch_catalog)
                )
                new_objects.update(
                    self._get_direct_dependents(obj_id, self.master_catalog)
                )
                new_objects.update(
                    self._get_direct_dependents(obj_id, self.branch_catalog)
                )

            if not new_objects - relevant:  # No new objects found
                break
            relevant.update(new_objects)

        return relevant

    def _get_direct_dependencies(self, obj_id: str, catalog: PgCatalog) -> set[str]:
        """Get direct dependencies of an object from a catalog."""
        dependencies = set()
        for depend in catalog.depends:
            if (
                depend.dependent_stable_id == obj_id
                and not depend.referenced_stable_id.startswith("unknown.")
            ):
                dependencies.add(depend.referenced_stable_id)
        return dependencies

    def _get_direct_dependents(self, obj_id: str, catalog: PgCatalog) -> set[str]:
        """Get direct dependents of an object from a catalog."""
        dependents = set()
        for depend in catalog.depends:
            if (
                depend.referenced_stable_id == obj_id
                and not depend.dependent_stable_id.startswith("unknown.")
            ):
                dependents.add(depend.dependent_stable_id)
        return dependents

    def _extract_from_catalog(
        self,
        model: DependencyModel,
        catalog: PgCatalog,
        relevant_objects: set[str],
        source: str,
    ) -> None:
        """Extract dependencies from a catalog for relevant objects only."""
        for depend in catalog.depends:
            if (
                depend.dependent_stable_id in relevant_objects
                and depend.referenced_stable_id in relevant_objects
                and not depend.dependent_stable_id.startswith("unknown.")
                and not depend.referenced_stable_id.startswith("unknown.")
            ):
                model.add_dependency(
                    depend.dependent_stable_id, depend.referenced_stable_id, source
                )


class OperationSemantics:
    """Defines semantic rules for ordering operations based on dependencies."""

    def generate_constraints(
        self, changes: list[DDL], model: DependencyModel
    ) -> list[Constraint]:
        """Generate ordering constraints from changes and dependency model."""
        constraints = []

        # Add dependency-based constraints
        constraints.extend(self._generate_dependency_constraints(changes, model))

        # Add same-object operation constraints
        constraints.extend(self._generate_same_object_constraints(changes))

        return constraints

    def _generate_dependency_constraints(
        self, changes: list[DDL], model: DependencyModel
    ) -> list[Constraint]:
        """Generate constraints based on object dependencies."""
        constraints = []

        for i, change_a in enumerate(changes):
            for j, change_b in enumerate(changes):
                if i == j:
                    continue

                # Determine which catalog state to use for dependency analysis
                constraint = self._analyze_dependency_constraint(
                    i, change_a, j, change_b, model
                )
                if constraint:
                    constraints.append(constraint)

        return constraints

    def _analyze_dependency_constraint(
        self, i: int, change_a: DDL, j: int, change_b: DDL, model: DependencyModel
    ) -> Constraint | None:
        """Analyze if two changes should be ordered based on dependencies."""
        # Choose appropriate catalog state for each operation
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

        # Check cross-catalog dependencies (V1's cross-catalog logic)
        cross_a_depends_on_b = (
            model.has_dependency(change_a.stable_id, change_b.stable_id, "source")
            and not a_depends_on_b  # Only if not already found in primary analysis
        )
        cross_b_depends_on_a = (
            model.has_dependency(change_b.stable_id, change_a.stable_id, "source")
            and not b_depends_on_a  # Only if not already found in primary analysis
        )

        # Apply semantic rules
        if a_depends_on_b or cross_a_depends_on_b:
            return self._dependency_semantic_rule(
                i, change_a, j, change_b, "a_depends_on_b"
            )
        elif b_depends_on_a or cross_b_depends_on_a:
            return self._dependency_semantic_rule(
                j, change_b, i, change_a, "b_depends_on_a"
            )

        return None

    def _dependency_semantic_rule(
        self,
        dep_idx: int,
        dependent_change: DDL,
        ref_idx: int,
        referenced_change: DDL,
        reason: str,
    ) -> Constraint | None:
        """Apply semantic rules when dependent_change depends on referenced_change."""
        # TODO: Investigate and eliminate all special cases

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

        # Rule: For DROP operations, drop dependents before dependencies
        if is_drop_change(dependent_change) and is_drop_change(referenced_change):
            return Constraint(
                dep_idx,
                ConstraintType.BEFORE,
                ref_idx,
                f"DROP dependent before dependency ({reason})",
            )

        # Rule: For CREATE operations, create dependencies before dependents
        elif is_create_change(dependent_change) and is_create_change(referenced_change):
            return Constraint(
                ref_idx,
                ConstraintType.BEFORE,
                dep_idx,
                f"CREATE dependency before dependent ({reason})",
            )

        # Rule: For mixed CREATE/ALTER/REPLACE, create dependencies first
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
                ref_idx,
                ConstraintType.BEFORE,
                dep_idx,
                f"Ensure dependency exists before dependent ({reason})",
            )

        # Rule: DROP before CREATE/ALTER/REPLACE
        elif is_drop_change(referenced_change) and (
            is_create_change(dependent_change)
            or is_alter_change(dependent_change)
            or is_replace_change(dependent_change)
        ):
            return Constraint(
                ref_idx,
                ConstraintType.BEFORE,
                dep_idx,
                f"DROP before CREATE/ALTER/REPLACE ({reason})",
            )

        return None

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
                # Sort by operation priority
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
            return 0
        elif is_create_change(change):
            return 1  # CREATE should come before ALTER for same object
        elif is_alter_change(change):
            return 2  # ALTER should come after CREATE for same object
        elif is_replace_change(change):
            return 3
        else:
            return 4


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
                graph.add_edge(constraint.change_a_index, constraint.change_b_index)

        # Topological sort
        try:
            ordered_indices = list(nx.topological_sort(graph))
            return [changes[i] for i in ordered_indices]
        except nx.NetworkXUnfeasible:
            raise CyclicDependencyError(
                "Cyclic dependency detected in change constraints"
            ) from None


class DependencyResolver:
    """Main dependency resolver using constraint-based architecture."""

    def __init__(self, master_catalog: PgCatalog, branch_catalog: PgCatalog):
        self.extractor = DependencyExtractor(master_catalog, branch_catalog)
        self.semantics = OperationSemantics()
        self.solver = ConstraintSolver()

    def resolve_dependencies(self, changes: list[DDL]) -> list[DDL]:
        """Resolve dependencies using constraint-based approach."""
        if not changes:
            return changes

        # Extract relevant dependencies
        dependency_model = self.extractor.extract_for_changeset(changes)

        # Generate constraints
        constraints = self.semantics.generate_constraints(changes, dependency_model)

        # Solve constraints
        return self.solver.solve(changes, constraints)


# Public interface matching other resolvers
def resolve_dependencies(
    changes: list[DDL],
    master_catalog: PgCatalog,
    branch_catalog: PgCatalog | None = None,
) -> list[DDL]:
    """
    Resolve dependencies using constraint-based approach.

    Args:
        changes: List of DDL changes to order
        master_catalog: The master catalog (current state)
        branch_catalog: The branch catalog (target state, optional)
    """
    if branch_catalog is None:
        from .catalog import catalog

        branch_catalog = catalog()

    resolver = DependencyResolver(master_catalog, branch_catalog)
    return resolver.resolve_dependencies(changes)
