"""Main diff orchestrator."""

from ..catalog import PgCatalog
from ..changes import DDL
from ..dependency_resolution import resolve_dependencies
from .pg_class_diff import diff_classes
from .pg_constraint_diff import diff_constraints
from .pg_index_diff import diff_indexes
from .pg_namespace_diff import diff_schemas
from .pg_policy_diff import diff_policies
from .pg_proc_diff import diff_procedures
from .pg_sequence_diff import diff_sequences
from .pg_trigger_diff import diff_triggers
from .pg_type_diff import diff_types


def diff_catalogs(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Generate changes to transform master catalog to branch catalog."""
    changes: list[DDL] = []

    # Diff schemas first
    changes.extend(diff_schemas(master, branch))

    # Diff types (before classes since tables may use custom types)
    changes.extend(diff_types(master, branch))

    # Diff sequences (before classes since SERIAL columns depend on sequences)
    changes.extend(diff_sequences(master, branch))

    # Diff classes (tables, views, etc.)
    changes.extend(diff_classes(master, branch))

    # Diff procedures/functions (before constraints since constraints may reference functions)
    changes.extend(diff_procedures(master, branch))

    # Diff constraints
    changes.extend(diff_constraints(master, branch))

    # Diff indexes
    changes.extend(diff_indexes(master, branch))

    # Diff RLS policies (after tables since policies depend on tables)
    changes.extend(diff_policies(master, branch))

    # Diff triggers (after functions since triggers depend on functions)
    changes.extend(diff_triggers(master, branch))

    # Apply dependency resolution to order changes correctly
    if changes:
        # Use appropriate catalog for each operation type:
        # - CREATE operations: use branch catalog (where new objects will exist)
        # - DROP operations: use master catalog (where objects to be dropped currently exist)
        changes = resolve_dependencies(changes, master, branch)

    return changes
