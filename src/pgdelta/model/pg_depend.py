"""PostgreSQL dependency model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from pgdelta.model import (
        PgClass,
        PgConstraint,
        PgIndex,
        PgNamespace,
        PgPolicy,
        PgProc,
        PgSequence,
        PgTrigger,
        PgType,
    )


@dataclass(slots=True, frozen=True)
class PgDepend:
    """PostgreSQL dependency model.

    Dependencies are used purely for ordering operations and don't participate
    in semantic schema comparison, so no field metadata is needed.
    """

    # Raw pg_depend fields with resolved classid names
    classid_name: str  # e.g., "pg_class", "pg_namespace", "pg_constraint"
    objid: int
    objsubid: int
    refclassid_name: str  # e.g., "pg_class", "pg_namespace", "pg_constraint"
    refobjid: int
    refobjsubid: int
    deptype: str

    # Resolved fields (computed during extraction)
    dependent_stable_id: str
    referenced_stable_id: str


def extract_depends(
    session: Session,
    namespaces: list[PgNamespace],
    classes: list[PgClass],
    constraints: list[PgConstraint],
    indexes: list[PgIndex],
    sequences: list[PgSequence],
    policies: list[PgPolicy],
    procedures: list[PgProc],
    triggers: list[PgTrigger],
    types: list[PgType],
) -> list[PgDepend]:
    """Extract dependencies from pg_depend."""
    # Build OID to stable_id mapping by classid name
    oid_to_stable_id = {}

    # Map namespace OIDs
    for namespace in namespaces:
        oid_to_stable_id[("pg_namespace", namespace.oid)] = namespace.stable_id

    # Map class OIDs (tables, views, etc.)
    for cls in classes:
        oid_to_stable_id[("pg_class", cls.oid)] = cls.stable_id

    # Map constraint OIDs
    for constraint in constraints:
        oid_to_stable_id[("pg_constraint", constraint.oid)] = constraint.stable_id

    # Map index OIDs (indexes also use pg_class)
    for index in indexes:
        oid_to_stable_id[("pg_class", index.oid)] = index.stable_id

    # Map sequence OIDs (sequences also use pg_class)
    for sequence in sequences:
        oid_to_stable_id[("pg_class", sequence.oid)] = sequence.stable_id

    # Map policy OIDs (policies use pg_policy)
    for policy in policies:
        oid_to_stable_id[("pg_policy", policy.oid)] = policy.stable_id

    # Map procedure OIDs (procedures use pg_proc)
    for procedure in procedures:
        oid_to_stable_id[("pg_proc", procedure.oid)] = procedure.stable_id

    # Map trigger OIDs (triggers use pg_trigger)
    for trigger in triggers:
        oid_to_stable_id[("pg_trigger", trigger.oid)] = trigger.stable_id

    # Map type OIDs (types use pg_type)
    for typ in types:
        oid_to_stable_id[("pg_type", typ.oid)] = typ.stable_id

    # Extract user object OIDs for filtering
    user_object_oids = [cls.oid for cls in classes]
    user_object_oids.extend([seq.oid for seq in sequences])
    user_namespace_oids = [ns.oid for ns in namespaces]
    user_constraint_oids = [constraint.oid for constraint in constraints]
    user_policy_oids = [policy.oid for policy in policies]
    user_procedure_oids = [procedure.oid for procedure in procedures]
    user_trigger_oids = [trigger.oid for trigger in triggers]
    user_type_oids = [typ.oid for typ in types]

    # Build query with joins to resolve classid names
    query = text(
        """
        SELECT DISTINCT
            d.objid,
            d.objsubid,
            d.refobjid,
            d.refobjsubid,
            d.deptype,
            c1.relname AS classid_name,
            c2.relname AS refclassid_name
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_class c1 ON d.classid = c1.oid
        JOIN pg_catalog.pg_class c2 ON d.refclassid = c2.oid
        WHERE d.deptype IN ('n', 'a', 'i')  -- normal, auto, internal dependencies
        AND c1.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pg_catalog')
        AND c2.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pg_catalog')
        AND (
            -- Include dependencies where dependent object is in user schemas
            (c1.relname = 'pg_class' AND d.objid = ANY(:user_oids))
            OR
            -- Include dependencies where referenced object is in user schemas
            (c2.relname = 'pg_class' AND d.refobjid = ANY(:user_oids))
            OR
            -- Include table->schema dependencies (dependent=table, referenced=schema)
            (c1.relname = 'pg_class' AND d.objid = ANY(:user_oids) AND c2.relname = 'pg_namespace' AND d.refobjid = ANY(:user_namespace_oids))
            OR
            -- Include constraint dependencies (dependent=constraint, referenced=table)
            (c1.relname = 'pg_constraint' AND d.objid = ANY(:user_constraint_oids))
            OR
            -- Include dependencies where referenced object is a constraint
            (c2.relname = 'pg_constraint' AND d.refobjid = ANY(:user_constraint_oids))
            OR
            -- Include policy dependencies (dependent=policy, referenced=table)
            (c1.relname = 'pg_policy' AND d.objid = ANY(:user_policy_oids))
            OR
            -- Include dependencies where referenced object is a policy
            (c2.relname = 'pg_policy' AND d.refobjid = ANY(:user_policy_oids))
            OR
            -- Include procedure dependencies (dependent=procedure, referenced=object)
            (c1.relname = 'pg_proc' AND d.objid = ANY(:user_procedure_oids))
            OR
            -- Include dependencies where referenced object is a procedure
            (c2.relname = 'pg_proc' AND d.refobjid = ANY(:user_procedure_oids))
            OR
            -- Include trigger dependencies (dependent=trigger, referenced=object)
            (c1.relname = 'pg_trigger' AND d.objid = ANY(:user_trigger_oids))
            OR
            -- Include dependencies where referenced object is a trigger
            (c2.relname = 'pg_trigger' AND d.refobjid = ANY(:user_trigger_oids))
            OR
            -- Include type dependencies (dependent=type, referenced=object)
            (c1.relname = 'pg_type' AND d.objid = ANY(:user_type_oids))
            OR
            -- Include dependencies where referenced object is a type
            (c2.relname = 'pg_type' AND d.refobjid = ANY(:user_type_oids))
        )
        ORDER BY d.objid, d.objsubid
    """
    )

    result = session.execute(
        query,
        {
            "user_oids": user_object_oids,
            "user_namespace_oids": user_namespace_oids,
            "user_constraint_oids": user_constraint_oids,
            "user_policy_oids": user_policy_oids,
            "user_procedure_oids": user_procedure_oids,
            "user_trigger_oids": user_trigger_oids,
            "user_type_oids": user_type_oids,
        },
    )
    depends = []

    for row in result:
        # Resolve stable IDs
        dependent_key = (row.classid_name, row.objid)
        referenced_key = (row.refclassid_name, row.refobjid)

        dependent_stable_id = oid_to_stable_id.get(
            dependent_key, f"unknown.{row.classid_name}.{row.objid}"
        )
        referenced_stable_id = oid_to_stable_id.get(
            referenced_key, f"unknown.{row.refclassid_name}.{row.refobjid}"
        )

        depend = PgDepend(
            classid_name=row.classid_name,
            objid=row.objid,
            objsubid=row.objsubid,
            refclassid_name=row.refclassid_name,
            refobjid=row.refobjid,
            refobjsubid=row.refobjsubid,
            deptype=row.deptype,
            dependent_stable_id=dependent_stable_id,
            referenced_stable_id=referenced_stable_id,
        )
        depends.append(depend)

    return depends


def extract_view_dependencies_as_pg_depend(
    session: Session,
    classes: list[PgClass],
) -> list[PgDepend]:
    """Extract view dependencies from pg_rewrite and transform them into pg_depend format.

    This extracts dependencies that views and materialized views have on tables/other views
    through pg_rewrite, and returns them as PgDepend objects so they can be processed by the
    existing dependency resolution infrastructure.
    """
    # Get all view OIDs for filtering (both regular views and materialized views)
    view_oids = [cls.oid for cls in classes if cls.relkind in ("v", "m")]

    if not view_oids:
        return []

    # Extract view dependencies from pg_rewrite via pg_depend with classid name resolution
    # Views depend on the objects they reference through their rewrite rules
    query = text("""
        SELECT DISTINCT
            d.objid,
            d.objsubid,
            d.refobjid,
            d.refobjsubid,
            d.deptype,
            c1.relname AS classid_name,
            c2.relname AS refclassid_name
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_class c1 ON d.classid = c1.oid
        JOIN pg_catalog.pg_class c2 ON d.refclassid = c2.oid
        JOIN pg_catalog.pg_rewrite r ON r.oid = d.objid
        WHERE c1.relname = 'pg_rewrite'  -- Dependencies from rewrite rules
        AND r.ev_class = ANY(:view_oids)  -- Only for our views
        AND c2.relname = 'pg_class'  -- Dependencies on tables/views
        AND d.deptype = 'n'  -- Normal dependencies only
        AND c1.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pg_catalog')
        AND c2.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pg_catalog')
        ORDER BY d.objid, d.refobjid
    """)

    # Build OID to stable_id mapping for tables, views, and materialized views
    oid_to_stable_id = {}
    for cls in classes:
        if cls.relkind in ("r", "v", "m"):  # tables, views, and materialized views
            oid_to_stable_id[cls.oid] = cls.stable_id

    result = session.execute(query, {"view_oids": view_oids})

    dependencies = []

    for row in result:
        # Find the view that owns this rewrite rule
        # We need to map from rewrite rule back to the view
        view_query = text("""
            SELECT ev_class FROM pg_catalog.pg_rewrite
            WHERE oid = :rewrite_oid
        """)
        view_result = session.execute(view_query, {"rewrite_oid": row.objid})
        view_oid_row = view_result.fetchone()

        if not view_oid_row:
            continue

        view_oid = view_oid_row.ev_class

        # Get stable IDs for the dependency relationship
        dependent_stable_id = oid_to_stable_id.get(view_oid)
        referenced_stable_id = oid_to_stable_id.get(row.refobjid)

        if dependent_stable_id and referenced_stable_id:
            # Create PgDepend object: view depends on referenced object
            depend = PgDepend(
                classid_name="pg_class",  # classid_name (view is in pg_class)
                objid=view_oid,  # objid (view OID)
                objsubid=0,  # objsubid (whole object dependency)
                refclassid_name=row.refclassid_name,  # refclassid_name
                refobjid=row.refobjid,  # refobjid
                refobjsubid=row.refobjsubid,  # refobjsubid
                deptype="n",  # deptype (normal dependency)
                dependent_stable_id=dependent_stable_id,
                referenced_stable_id=referenced_stable_id,
            )
            dependencies.append(depend)

    return dependencies
