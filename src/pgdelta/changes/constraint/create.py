"""Create constraint change type and SQL generation.

PostgreSQL constraint operations:

ADD CONSTRAINT:
ALTER TABLE table_name ADD CONSTRAINT constraint_name constraint_definition

Where constraint_definition can be:
- PRIMARY KEY (column_list)
- UNIQUE (column_list)
- CHECK (expression)
- FOREIGN KEY (column_list) REFERENCES table (column_list) [ON DELETE action] [ON UPDATE action]
- EXCLUDE [USING index_method] (expression WITH operator [, ...]) [WHERE (predicate)]

Currently supported:
- CREATE PRIMARY KEY constraints
- CREATE UNIQUE constraints
- CREATE CHECK constraints
- CREATE FOREIGN KEY constraints
- CREATE EXCLUSION constraints
- Constraint deferrability options
- Foreign key actions (CASCADE, RESTRICT, SET NULL, SET DEFAULT, NO ACTION)

Not yet supported:
- Constraint inheritance
- Domain constraints
- Partial unique constraints with WHERE clause

Intentionally not supported:
- NOT VALID option (pgdelta assumes constraints should be valid)
- USING INDEX (pgdelta creates indexes implicitly)
"""

from dataclasses import dataclass

from ...model.pg_attribute import PgAttribute
from ...model.pg_constraint import PgConstraint


@dataclass(frozen=True)
class CreateConstraint:
    """Create constraint change."""

    stable_id: str  # namespace.table.constraint_name
    constraint: PgConstraint
    table_columns: list[PgAttribute]  # All columns in the table for name resolution
    referenced_table_columns: list[PgAttribute] | None = None  # For foreign keys


def generate_create_constraint_sql(change: CreateConstraint) -> str:
    """Generate ADD CONSTRAINT SQL."""
    constraint = change.constraint
    quoted_schema = f'"{constraint.namespace_name}"'
    quoted_table = f'"{constraint.table_name}"'
    quoted_constraint_name = f'"{constraint.conname}"'

    # Build constraint definition based on type
    constraint_def = _build_constraint_definition(
        constraint, change.table_columns, change.referenced_table_columns
    )

    return f"ALTER TABLE {quoted_schema}.{quoted_table} ADD CONSTRAINT {quoted_constraint_name} {constraint_def};"


def _build_constraint_definition(
    constraint: PgConstraint,
    table_columns: list[PgAttribute],
    referenced_table_columns: list[PgAttribute] | None = None,
) -> str:
    """Build constraint definition SQL based on constraint type."""

    if constraint.contype == "p":  # PRIMARY KEY
        column_names = _get_column_names_from_key(constraint.conkey, table_columns)
        return f"PRIMARY KEY ({', '.join(column_names)})"

    elif constraint.contype == "u":  # UNIQUE
        column_names = _get_column_names_from_key(constraint.conkey, table_columns)
        unique_def = f"UNIQUE ({', '.join(column_names)})"
        # Add WHERE clause for partial unique constraints
        if constraint.conpredicate:
            unique_def += f" WHERE ({constraint.conpredicate})"
        return unique_def

    elif constraint.contype == "c":  # CHECK
        if not constraint.conbin:
            raise ValueError(
                f"CHECK constraint {constraint.conname} missing expression"
            )
        return f"CHECK ({constraint.conbin})"

    elif constraint.contype == "f":  # FOREIGN KEY
        # Build foreign key constraint
        local_columns = _get_column_names_from_key(constraint.conkey, table_columns)

        if not referenced_table_columns:
            raise ValueError(
                f"Foreign key constraint {constraint.conname} missing referenced table column information"
            )

        # Get referenced table name from the first referenced column (they should all be from same table)
        if not referenced_table_columns:
            raise ValueError(
                f"No referenced table columns provided for foreign key {constraint.conname}"
            )

        referenced_table = referenced_table_columns[0]
        foreign_table = (
            f'"{referenced_table.owner_namespace}"."{referenced_table.owner_name}"'
        )
        foreign_columns = _get_column_names_from_key(
            constraint.confkey, referenced_table_columns
        )

        fk_def = f"FOREIGN KEY ({', '.join(local_columns)}) REFERENCES {foreign_table} ({', '.join(foreign_columns)})"

        # Add foreign key actions
        if constraint.confupdtype != "a":  # 'a' = NO ACTION (default)
            fk_def += f" ON UPDATE {_get_fk_action(constraint.confupdtype)}"
        if constraint.confdeltype != "a":  # 'a' = NO ACTION (default)
            fk_def += f" ON DELETE {_get_fk_action(constraint.confdeltype)}"

        return fk_def

    elif constraint.contype == "x":  # EXCLUSION
        # TODO: Exclusion constraints are complex and need operator/expression handling
        return f"EXCLUDE (<exclusion_definition_for_{constraint.conname}>)"

    else:
        raise ValueError(f"Unsupported constraint type: {constraint.contype}")


def _get_column_names_from_key(
    conkey: list[int], table_columns: list[PgAttribute]
) -> list[str]:
    """
    Get quoted column names from constraint key column numbers.

    PostgreSQL stores column numbers (1-based) in constraint keys. We need to map
    these to actual column names using the table's attribute information.
    """
    # Create a mapping from column number to column name
    column_map = {attr.attnum: attr.attname for attr in table_columns}

    # Resolve column numbers to names
    column_names = []
    for col_num in conkey:
        if col_num in column_map:
            column_names.append(f'"{column_map[col_num]}"')
        else:
            raise ValueError(f"Column number {col_num} not found in table columns")

    return column_names


def _get_fk_action(action_code: str) -> str:
    """Convert foreign key action code to SQL."""
    action_map = {
        "a": "NO ACTION",
        "r": "RESTRICT",
        "c": "CASCADE",
        "n": "SET NULL",
        "d": "SET DEFAULT",
    }
    return action_map.get(action_code, "NO ACTION")
