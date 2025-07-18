"""Create sequence operations.

PostgreSQL 17 CREATE SEQUENCE Synopsis:
https://www.postgresql.org/docs/17/sql-createsequence.html

CREATE [ { TEMPORARY | TEMP } | UNLOGGED ] SEQUENCE [ IF NOT EXISTS ] name
    [ AS data_type ]
    [ INCREMENT [ BY ] increment ]
    [ MINVALUE minvalue | NO MINVALUE ]
    [ MAXVALUE maxvalue | NO MAXVALUE ]
    [ START [ WITH ] start ]
    [ CACHE cache ]
    [ [ NO ] CYCLE ]
    [ OWNED BY { table_name.column_name | NONE } ]

Currently supported:
- Basic sequence creation with name
- Data type specification (smallint, integer, bigint)
- INCREMENT BY values
- MINVALUE/MAXVALUE bounds
- START WITH initial value
- CACHE settings
- CYCLE/NO CYCLE behavior
- OWNED BY table column associations

Not yet supported:
- None (all standard sequence parameters are supported)

Intentionally not supported:
- TEMPORARY/TEMP sequences (not persistent schema objects)
- UNLOGGED sequences (storage detail)
- IF NOT EXISTS (pgdelta tracks existence)
"""

from dataclasses import dataclass

from ...model import PgSequence


@dataclass(frozen=True)
class CreateSequence:
    """Create a sequence."""

    stable_id: str
    sequence: PgSequence


def generate_create_sequence_sql(change: CreateSequence) -> str:
    """Generate SQL for creating a sequence."""
    parts = [
        f'CREATE SEQUENCE "{change.sequence.namespace}"."{change.sequence.seqname}"'
    ]

    # Add data type if not default (bigint)
    if change.sequence.data_type != "bigint":
        parts.append(f"AS {change.sequence.data_type}")

    # Add increment
    if change.sequence.increment_by != 1:
        parts.append(f"INCREMENT BY {change.sequence.increment_by}")

    # Add min value
    if change.sequence.min_value is not None:
        parts.append(f"MINVALUE {change.sequence.min_value}")
    else:
        parts.append("NO MINVALUE")

    # Add max value
    if change.sequence.max_value is not None:
        parts.append(f"MAXVALUE {change.sequence.max_value}")
    else:
        parts.append("NO MAXVALUE")

    # Add start value
    if change.sequence.start_value != 1:
        parts.append(f"START WITH {change.sequence.start_value}")

    # Add cache
    if change.sequence.cache_size != 1:
        parts.append(f"CACHE {change.sequence.cache_size}")

    # Add cycle
    if change.sequence.cycle:
        parts.append("CYCLE")
    else:
        parts.append("NO CYCLE")

    # Skip OWNED BY clause - ownership is handled by CREATE TABLE or ALTER SEQUENCE commands
    # when the table with the SERIAL column references the sequence
    return " ".join(parts) + ";"
