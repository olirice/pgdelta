"""CREATE TYPE SQL generation.

PostgreSQL 17 CREATE TYPE Synopsis:
https://www.postgresql.org/docs/17/sql-createtype.html

CREATE TYPE name AS (
    [attribute_name data_type [COLLATE collation] [, ...]]
)

CREATE TYPE name AS ENUM (
    ['label' [, ...]]
)

CREATE TYPE name AS RANGE (
    SUBTYPE = subtype
    [, SUBTYPE_OPCLASS = subtype_operator_class]
    [, COLLATION = collation]
    [, CANONICAL = canonical_function]
    [, SUBTYPE_DIFF = subtype_diff_function]
    [, MULTIRANGE_TYPE_NAME = multirange_type_name]
)

CREATE TYPE name (
    INPUT = input_function
    , OUTPUT = output_function
    [, RECEIVE = receive_function]
    [, SEND = send_function]
    [, TYPMOD_IN = typmod_in_function]
    [, TYPMOD_OUT = typmod_out_function]
    [, ANALYZE = analyze_function]
    [, INTERNALLENGTH = { internallength | VARIABLE }]
    [, PASSEDBYVALUE]
    [, ALIGNMENT = alignment]
    [, STORAGE = storage]
    [, LIKE = like_type]
    [, CATEGORY = category]
    [, PREFERRED = preferred]
    [, DEFAULT = default]
    [, ELEMENT = element]
    [, DELIMITER = delimiter]
    [, COLLATABLE = collatable]
    [, SUBSCRIPT = subscript_function]
)

CREATE TYPE name

Currently supported:
- Composite types with attribute definitions
- Enum types with labels
- Range types with subtype configuration
- Multirange types
- Domain types with base type and constraints
- Basic shell type creation

Not yet supported:
- Base types with custom I/O functions
- Advanced base type parameters (ALIGNMENT, STORAGE, etc.)
- LIKE clause for base types
- CATEGORY and PREFERRED settings
- ELEMENT and DELIMITER for array-like types
- COLLATABLE setting
- SUBSCRIPT functions

Intentionally not supported:
- None (all type creation features are valid for DDL generation)
"""

from dataclasses import dataclass

from pgdelta.model.pg_type import CompositeAttribute


@dataclass(frozen=True)
class CreateType:
    """CREATE TYPE change."""

    stable_id: str
    namespace: str
    typname: str
    typtype: (
        str  # 'b'=base, 'e'=enum, 'd'=domain, 'c'=composite, 'r'=range, 'm'=multirange
    )

    # Type-specific data
    enum_values: list[str] | None = None  # For enum types
    domain_base_type: str | None = None  # For domain types
    domain_constraints: list[str] | None = None  # For domain types
    composite_attributes: list[CompositeAttribute] | None = None  # For composite types
    range_subtype: str | None = None  # For range types
    range_subtype_diff: str | None = None  # For range types
    range_canonical: str | None = None  # For range types
    range_subtype_opclass: str | None = None  # For range types
    range_collation: str | None = None  # For range types
    multirange_range_type: str | None = None  # For multirange types

    # Base type properties (for typtype = 'b')
    base_input_function: str | None = None  # INPUT function name
    base_output_function: str | None = None  # OUTPUT function name
    base_receive_function: str | None = None  # Optional RECEIVE function
    base_send_function: str | None = None  # Optional SEND function
    base_typmod_in_function: str | None = None  # Optional typmod input function
    base_typmod_out_function: str | None = None  # Optional typmod output function
    base_analyze_function: str | None = None  # Optional analyze function
    base_internallength: int | None = None  # INTERNALLENGTH
    base_passedbyvalue: bool | None = None  # PASSEDBYVALUE
    base_alignment: str | None = None  # ALIGNMENT (char, int2, int4, double)
    base_storage: str | None = None  # STORAGE (plain, external, extended, main)
    base_like_type: str | None = None  # LIKE type_name
    base_category: str | None = None  # CATEGORY
    base_preferred: bool | None = None  # PREFERRED
    base_default: str | None = None  # DEFAULT value
    base_element: str | None = None  # ELEMENT type for array types
    base_delimiter: str | None = None  # DELIMITER character
    base_collatable: bool | None = None  # COLLATABLE


def generate_create_type_sql(change: CreateType) -> str:
    """Generate CREATE TYPE SQL statement."""
    quoted_schema = f'"{change.namespace}"'
    quoted_name = f'"{change.typname}"'
    qualified_name = f"{quoted_schema}.{quoted_name}"

    if change.typtype == "b":  # Base type
        if not change.base_input_function or not change.base_output_function:
            raise ValueError(
                f"Base type {change.stable_id} must have input and output functions"
            )

        sql = f"CREATE TYPE {qualified_name} ("
        options = []

        # Required functions
        options.append(f"INPUT = {change.base_input_function}")
        options.append(f"OUTPUT = {change.base_output_function}")

        # Optional functions
        if change.base_receive_function:
            options.append(f"RECEIVE = {change.base_receive_function}")
        if change.base_send_function:
            options.append(f"SEND = {change.base_send_function}")
        if change.base_typmod_in_function:
            options.append(f"TYPMOD_IN = {change.base_typmod_in_function}")
        if change.base_typmod_out_function:
            options.append(f"TYPMOD_OUT = {change.base_typmod_out_function}")
        if change.base_analyze_function:
            options.append(f"ANALYZE = {change.base_analyze_function}")

        # Type properties
        if change.base_internallength is not None:
            if change.base_internallength == -1:
                options.append("INTERNALLENGTH = VARIABLE")
            else:
                options.append(f"INTERNALLENGTH = {change.base_internallength}")

        if change.base_passedbyvalue is not None:
            options.append(f"PASSEDBYVALUE = {str(change.base_passedbyvalue).upper()}")

        if change.base_alignment:
            options.append(f"ALIGNMENT = {change.base_alignment}")

        if change.base_storage:
            options.append(f"STORAGE = {change.base_storage}")

        if change.base_like_type:
            options.append(f"LIKE = {change.base_like_type}")

        if change.base_category:
            options.append(f"CATEGORY = '{change.base_category}'")

        if change.base_preferred is not None:
            options.append(f"PREFERRED = {str(change.base_preferred).upper()}")

        if change.base_default:
            options.append(f"DEFAULT = '{change.base_default}'")

        if change.base_element:
            options.append(f"ELEMENT = {change.base_element}")

        if change.base_delimiter:
            options.append(f"DELIMITER = '{change.base_delimiter}'")

        if change.base_collatable is not None:
            options.append(f"COLLATABLE = {str(change.base_collatable).upper()}")

        sql += ",\n    ".join(options)
        sql += ");"
        return sql

    elif change.typtype == "e":  # Enum type
        if not change.enum_values:
            raise ValueError(f"Enum type {change.stable_id} must have enum_values")

        # Quote each enum value and join with commas
        quoted_values = [f"'{value}'" for value in change.enum_values]
        values_str = ", ".join(quoted_values)

        return f"CREATE TYPE {qualified_name} AS ENUM ({values_str});"

    elif change.typtype == "d":  # Domain type
        if not change.domain_base_type:
            raise ValueError(
                f"Domain type {change.stable_id} must have domain_base_type"
            )

        sql = f"CREATE DOMAIN {qualified_name} AS {change.domain_base_type}"

        # Add constraints if any
        if change.domain_constraints:
            for constraint in change.domain_constraints:
                # pg_get_constraintdef() returns the complete constraint definition
                sql += f" {constraint.strip()}"

        return sql + ";"

    elif change.typtype == "c":  # Composite type
        if not change.composite_attributes:
            raise ValueError(
                f"Composite type {change.stable_id} must have composite_attributes"
            )

        # Build attribute definitions
        attr_defs = []
        for attr in change.composite_attributes:
            attr_name = f'"{attr.name}"'
            attr_type = attr.type_name

            attr_def = f"{attr_name} {attr_type}"
            if attr.not_null:
                attr_def += " NOT NULL"

            attr_defs.append(attr_def)

        attributes_str = ",\n    ".join(attr_defs)
        return f"CREATE TYPE {qualified_name} AS (\n    {attributes_str}\n);"

    elif change.typtype == "r":  # Range type
        if not change.range_subtype:
            raise ValueError(f"Range type {change.stable_id} must have range_subtype")

        sql = f"CREATE TYPE {qualified_name} AS RANGE ("
        options = [f"subtype = {change.range_subtype}"]

        if change.range_subtype_diff:
            options.append(f"subtype_diff = {change.range_subtype_diff}")
        if change.range_canonical:
            options.append(f"canonical = {change.range_canonical}")
        if change.range_subtype_opclass:
            options.append(f"subtype_opclass = {change.range_subtype_opclass}")
        if change.range_collation:
            options.append(f"collation = {change.range_collation}")

        sql += ", ".join(options)
        sql += ");"
        return sql

    elif change.typtype == "m":  # Multirange type
        if not change.multirange_range_type:
            raise ValueError(
                f"Multirange type {change.stable_id} must have multirange_range_type"
            )

        return f"CREATE TYPE {qualified_name} AS MULTIRANGE (range_type = {change.multirange_range_type});"

    else:
        raise ValueError(
            f"Unsupported type category: {change.typtype} for {change.stable_id}"
        )
