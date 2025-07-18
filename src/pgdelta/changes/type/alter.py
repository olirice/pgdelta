"""ALTER TYPE SQL generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AlterTypeOwnerTo:
    """ALTER TYPE ... OWNER TO change."""

    stable_id: str
    namespace: str
    typname: str
    new_owner: str


@dataclass(frozen=True)
class AlterTypeRename:
    """ALTER TYPE ... RENAME TO change."""

    stable_id: str
    namespace: str
    typname: str
    new_name: str


@dataclass(frozen=True)
class AlterTypeSetSchema:
    """ALTER TYPE ... SET SCHEMA change."""

    stable_id: str
    namespace: str
    typname: str
    new_schema: str


@dataclass(frozen=True)
class AlterTypeAddAttribute:
    """ALTER TYPE ... ADD ATTRIBUTE change (for composite types)."""

    stable_id: str
    namespace: str
    typname: str
    attribute_name: str
    attribute_type: str


@dataclass(frozen=True)
class AlterTypeDropAttribute:
    """ALTER TYPE ... DROP ATTRIBUTE change (for composite types)."""

    stable_id: str
    namespace: str
    typname: str
    attribute_name: str


@dataclass(frozen=True)
class AlterTypeAlterAttribute:
    """ALTER TYPE ... ALTER ATTRIBUTE ... TYPE change (for composite types)."""

    stable_id: str
    namespace: str
    typname: str
    attribute_name: str
    new_type: str


@dataclass(frozen=True)
class AlterTypeAddValue:
    """ALTER TYPE ... ADD VALUE change (for enum types)."""

    stable_id: str
    namespace: str
    typname: str
    new_value: str
    before_value: str | None = None
    after_value: str | None = None


@dataclass(frozen=True)
class AlterTypeRenameValue:
    """ALTER TYPE ... RENAME VALUE change (for enum types)."""

    stable_id: str
    namespace: str
    typname: str
    old_value: str
    new_value: str


# Union type for all ALTER TYPE changes
AlterTypeChange = (
    AlterTypeOwnerTo
    | AlterTypeRename
    | AlterTypeSetSchema
    | AlterTypeAddAttribute
    | AlterTypeDropAttribute
    | AlterTypeAlterAttribute
    | AlterTypeAddValue
    | AlterTypeRenameValue
)


def generate_alter_type_sql(change: AlterTypeChange) -> str:
    """Generate ALTER TYPE SQL statement."""
    quoted_schema = f'"{change.namespace}"'
    quoted_name = f'"{change.typname}"'
    qualified_name = f"{quoted_schema}.{quoted_name}"

    if isinstance(change, AlterTypeOwnerTo):
        return f"ALTER TYPE {qualified_name} OWNER TO {change.new_owner};"

    elif isinstance(change, AlterTypeRename):
        quoted_new_name = f'"{change.new_name}"'
        return f"ALTER TYPE {qualified_name} RENAME TO {quoted_new_name};"

    elif isinstance(change, AlterTypeSetSchema):
        quoted_new_schema = f'"{change.new_schema}"'
        return f"ALTER TYPE {qualified_name} SET SCHEMA {quoted_new_schema};"

    elif isinstance(change, AlterTypeAddAttribute):
        quoted_attr_name = f'"{change.attribute_name}"'
        return f"ALTER TYPE {qualified_name} ADD ATTRIBUTE {quoted_attr_name} {change.attribute_type};"

    elif isinstance(change, AlterTypeDropAttribute):
        quoted_attr_name = f'"{change.attribute_name}"'
        return f"ALTER TYPE {qualified_name} DROP ATTRIBUTE {quoted_attr_name};"

    elif isinstance(change, AlterTypeAlterAttribute):
        quoted_attr_name = f'"{change.attribute_name}"'
        return f"ALTER TYPE {qualified_name} ALTER ATTRIBUTE {quoted_attr_name} TYPE {change.new_type};"

    elif isinstance(change, AlterTypeAddValue):
        sql = f"ALTER TYPE {qualified_name} ADD VALUE '{change.new_value}'"

        if change.before_value:
            sql += f" BEFORE '{change.before_value}'"
        elif change.after_value:
            sql += f" AFTER '{change.after_value}'"

        return sql + ";"

    elif isinstance(change, AlterTypeRenameValue):
        sql = f"ALTER TYPE {qualified_name} RENAME VALUE '{change.old_value}' TO '{change.new_value}'"
        return sql + ";"

    else:
        raise ValueError(f"Unsupported ALTER TYPE change: {type(change)}")
