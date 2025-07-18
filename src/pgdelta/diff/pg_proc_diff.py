"""Procedure (function) diff logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..catalog import PgCatalog
from ..changes import DDL

if TYPE_CHECKING:
    from ..model import PgProc


def diff_procedures(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Diff procedures (functions) between catalogs."""
    changes: list[DDL] = []

    # Get all unique stable_ids to process
    all_proc_ids = set(master.procedures.keys()) | set(branch.procedures.keys())

    for proc_id in all_proc_ids:
        master_proc: PgProc | None = master.procedures.get(proc_id)
        branch_proc: PgProc | None = branch.procedures.get(proc_id)

        if master_proc is None and branch_proc is not None:
            # Function was added
            from ..changes.function import CreateFunction

            changes.append(CreateFunction(procedure=branch_proc))
        elif master_proc is not None and branch_proc is None:
            # Function was removed
            from ..changes.function import DropFunction

            changes.append(DropFunction(procedure=master_proc))
        elif master_proc is not None and branch_proc is not None:
            # Function exists in both - check if it changed
            if not master_proc.semantic_equality(branch_proc):
                # Function changed - need to replace it
                from ..changes.function import ReplaceFunction

                changes.append(
                    ReplaceFunction(
                        old_procedure=master_proc, new_procedure=branch_proc
                    )
                )

    return changes
