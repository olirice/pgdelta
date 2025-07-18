"""Alter sequence operations."""

from dataclasses import dataclass

from ...model import PgSequence


@dataclass(frozen=True)
class AlterSequence:
    """Alter a sequence."""

    stable_id: str
    old_sequence: PgSequence
    new_sequence: PgSequence


def generate_alter_sequence_sql(change: AlterSequence) -> str:
    """Generate SQL for altering a sequence."""
    parts = [
        f'ALTER SEQUENCE "{change.new_sequence.namespace}"."{change.new_sequence.seqname}"'
    ]
    changes = []

    # Check data type
    if change.old_sequence.data_type != change.new_sequence.data_type:
        changes.append(f"AS {change.new_sequence.data_type}")

    # Check increment
    if change.old_sequence.increment_by != change.new_sequence.increment_by:
        changes.append(f"INCREMENT BY {change.new_sequence.increment_by}")

    # Check min value
    if change.old_sequence.min_value != change.new_sequence.min_value:
        if change.new_sequence.min_value is not None:
            changes.append(f"MINVALUE {change.new_sequence.min_value}")
        else:
            changes.append("NO MINVALUE")

    # Check max value
    if change.old_sequence.max_value != change.new_sequence.max_value:
        if change.new_sequence.max_value is not None:
            changes.append(f"MAXVALUE {change.new_sequence.max_value}")
        else:
            changes.append("NO MAXVALUE")

    # Check cache
    if change.old_sequence.cache_size != change.new_sequence.cache_size:
        changes.append(f"CACHE {change.new_sequence.cache_size}")

    # Check cycle
    if change.old_sequence.cycle != change.new_sequence.cycle:
        if change.new_sequence.cycle:
            changes.append("CYCLE")
        else:
            changes.append("NO CYCLE")

    # Check owned by (requires separate ALTER statements)
    owned_by_changed = (
        change.old_sequence.owned_by_table != change.new_sequence.owned_by_table
        or change.old_sequence.owned_by_column != change.new_sequence.owned_by_column
    )

    if not changes and not owned_by_changed:
        # No changes needed
        return ""

    sql_statements = []

    # Add main ALTER SEQUENCE statement if there are property changes
    if changes:
        sql_statements.append(" ".join(parts + changes) + ";")

    # Add owned by change if needed
    if owned_by_changed:
        if change.new_sequence.owned_by_table and change.new_sequence.owned_by_column:
            owned_by_sql = (
                f'ALTER SEQUENCE "{change.new_sequence.namespace}"."{change.new_sequence.seqname}" '
                f'OWNED BY "{change.new_sequence.namespace}"."{change.new_sequence.owned_by_table}"."{change.new_sequence.owned_by_column}";'
            )
        else:
            owned_by_sql = (
                f'ALTER SEQUENCE "{change.new_sequence.namespace}"."{change.new_sequence.seqname}" '
                "OWNED BY NONE;"
            )
        sql_statements.append(owned_by_sql)

    return "\n".join(sql_statements)
