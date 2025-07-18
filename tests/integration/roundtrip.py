"""
Test configuration and fixtures for pgdelta integration tests.
"""

from sqlalchemy import text

from pgdelta.catalog import extract_catalog
from pgdelta.changes.dispatcher import generate_sql


def roundtrip_fidelity_test(
    master_session,
    branch_session,
    initial_setup: str | None,
    test_sql: str | None,
    description: str,
    expected_sql_terms: list[str],
    expected_master_dependencies: list[tuple[str, str]],
    expected_branch_dependencies: list[tuple[str, str]],
    expected_operation_order: list[str] | None = None,
):
    """
    Test that schema extraction, SQL generation, and re-execution produces
    functionally identical pg_catalog data.

    This validates the core roundtrip fidelity:
    1. Extract catalog from master database (master_session)
    2. Extract catalog from branch database (branch_session)
    3. Generate migration from master to branch
    4. Apply migration to master database
    5. Verify master and branch catalogs are now semantically identical

    Args:
        master_session: Database session for the master database
        branch_session: Database session for the branch database
        initial_setup: Optional SQL to run in both databases before the test
        test_sql: SQL to run in branch database only
        description: Human-readable description of what's being tested
        expected_sql_terms: List of terms that must appear in the generated SQL
        expected_master_dependencies: List of (dependent, referenced) tuples that must be present in master catalog.
        expected_branch_dependencies: List of (dependent, referenced) tuples that must be present in branch catalog.
        expected_operation_order: Optional list of stable_ids in the order they should appear
                                 in the generated changes (validates dependency resolution ordering).
    """
    # Set up initial schema in BOTH databases
    if initial_setup:
        master_session.execute(text(initial_setup))
        branch_session.execute(text(initial_setup))

    # Execute the test SQL in the BRANCH database only
    if test_sql:
        branch_session.execute(text(test_sql))

    master_session.commit()
    branch_session.commit()

    # Extract catalogs from both databases
    master_catalog = extract_catalog(master_session)
    branch_catalog = extract_catalog(branch_session)

    # Validate dependencies using separated approach
    validate_separate_dependencies(
        master_catalog,
        branch_catalog,
        expected_master_dependencies,
        expected_branch_dependencies,
        description,
    )

    # Generate migration from master to branch
    changes = master_catalog.diff(branch_catalog)

    # Validate operation order if expected_operation_order is provided
    if expected_operation_order is not None:
        actual_order = [change.stable_id for change in changes]
        if actual_order != expected_operation_order:
            raise AssertionError(
                f"Operation order validation failed for {description}\n"
                f"Expected order: {expected_operation_order}\n"
                f"Actual order:   {actual_order}"
            )

    # Generate SQL from changes
    sql_statements = []
    for change in changes:
        sql = generate_sql(change)
        sql_statements.append(sql)

    # Join SQL statements (each already includes semicolon)
    generated_sql = "\n".join(sql_statements)

    # Verify expected terms are present in generated SQL
    for term in expected_sql_terms:
        if term not in generated_sql:
            print(f"\n\nDEBUG: Failed term '{term}' not found in:")
            print(f"Generated SQL: '{generated_sql}'")
            print(f"All expected terms: {expected_sql_terms}")
            print(f"Test: {description}\n")
        assert term in generated_sql, (
            f"Expected term '{term}' not found in generated SQL for {description}"
        )

    # Apply migration to master database
    if generated_sql.strip():
        # Execute the complete SQL (each statement already ends with semicolon)
        # Note: Don't split by semicolon as functions contain semicolons in their bodies
        master_session.execute(text(generated_sql))

    master_session.commit()

    # Extract final catalog from master database
    master_catalog_after = extract_catalog(master_session)

    # Verify semantic equality between master and branch catalogs
    assert branch_catalog.semantically_equals(master_catalog_after), (
        f"Catalogs are not semantically equal for {description}"
    )


def validate_separate_dependencies(
    master_catalog,
    branch_catalog,
    expected_master_dependencies: list[tuple[str, str]],
    expected_branch_dependencies: list[tuple[str, str]],
    description: str,
) -> None:
    """
    Validate dependencies separately for master and branch catalogs.

    This provides more precise validation by checking:
    - Master catalog dependencies match expected_master_dependencies exactly
    - Branch catalog dependencies match expected_branch_dependencies exactly
    """
    # Extract dependencies from master catalog
    master_deps = {
        (dep.dependent_stable_id, dep.referenced_stable_id)
        for dep in master_catalog.depends
        if not (
            dep.dependent_stable_id.startswith("unknown.")
            or dep.referenced_stable_id.startswith("unknown.")
        )
    }

    # Extract dependencies from branch catalog
    branch_deps = {
        (dep.dependent_stable_id, dep.referenced_stable_id)
        for dep in branch_catalog.depends
        if not (
            dep.dependent_stable_id.startswith("unknown.")
            or dep.referenced_stable_id.startswith("unknown.")
        )
    }

    expected_master_set = set(expected_master_dependencies)
    expected_branch_set = set(expected_branch_dependencies)

    # Validate master dependencies
    missing_master_deps = expected_master_set - master_deps
    unexpected_master_deps = master_deps - expected_master_set

    # Validate branch dependencies
    missing_branch_deps = expected_branch_set - branch_deps
    unexpected_branch_deps = branch_deps - expected_branch_set

    # Build detailed error message if validation fails
    if (
        missing_master_deps
        or unexpected_master_deps
        or missing_branch_deps
        or unexpected_branch_deps
    ):
        error_parts = [f"Dependency validation failed for {description}"]

        if missing_master_deps:
            error_parts.append("\\nMissing expected master dependencies:")
            for dep, ref in sorted(missing_master_deps):
                error_parts.append(f"  - {dep} → {ref}")

        if unexpected_master_deps:
            error_parts.append("\\nUnexpected master dependencies found:")
            for dep, ref in sorted(unexpected_master_deps):
                error_parts.append(f"  - {dep} → {ref}")

        if missing_branch_deps:
            error_parts.append("\\nMissing expected branch dependencies:")
            for dep, ref in sorted(missing_branch_deps):
                error_parts.append(f"  - {dep} → {ref}")

        if unexpected_branch_deps:
            error_parts.append("\\nUnexpected branch dependencies found:")
            for dep, ref in sorted(unexpected_branch_deps):
                error_parts.append(f"  - {dep} → {ref}")

        error_parts.append("\\nActual master dependencies:")
        for dep, ref in sorted(master_deps):
            error_parts.append(f"  - {dep} → {ref}")

        error_parts.append("\\nActual branch dependencies:")
        for dep, ref in sorted(branch_deps):
            error_parts.append(f"  - {dep} → {ref}")

        raise AssertionError("".join(error_parts))
