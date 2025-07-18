"""Drop sequence operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DropSequence:
    """Drop a sequence."""

    stable_id: str
    namespace: str
    seqname: str


def generate_drop_sequence_sql(change: DropSequence) -> str:
    """Generate SQL for dropping a sequence."""
    return f'DROP SEQUENCE "{change.namespace}"."{change.seqname}";'
