"""Schema diff logic."""

from ..catalog import PgCatalog
from ..changes import DDL, CreateSchema, DropSchema


def diff_schemas(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Diff schemas between catalogs."""
    changes: list[DDL] = []

    all_schema_ids = set(master.namespaces.keys()) | set(branch.namespaces.keys())

    for schema_id in all_schema_ids:
        master_schema = master.namespaces.get(schema_id)
        branch_schema = branch.namespaces.get(schema_id)

        match (master_schema, branch_schema):
            case (None, branch_schema) if branch_schema is not None:
                # Create new schema (but skip public schema as it always exists)
                # TODO: should we add public schema in an empty catalog to skip
                # this check? public is included in the defalut template but that
                # is not required
                if branch_schema.nspname != "public":
                    changes.append(
                        CreateSchema(
                            stable_id=branch_schema.stable_id,
                            nspname=branch_schema.nspname,
                        )
                    )
            case (master_schema, None) if master_schema is not None:
                # Drop schema
                changes.append(
                    DropSchema(
                        stable_id=master_schema.stable_id,
                        nspname=master_schema.nspname,
                    )
                )
            case (master_schema, branch_schema) if (
                master_schema is not None and branch_schema is not None
            ):
                # Schema exists in both - check for changes
                if not master_schema.semantic_equality(branch_schema):
                    # TODO: Implement schema alterations when needed
                    pass

    return changes
