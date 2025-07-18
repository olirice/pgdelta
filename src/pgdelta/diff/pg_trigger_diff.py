"""Trigger diff logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..catalog import PgCatalog
from ..changes import DDL

if TYPE_CHECKING:
    from ..model import PgTrigger


def diff_triggers(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Diff triggers between catalogs."""
    changes: list[DDL] = []

    # Get all unique stable_ids to process
    all_trigger_ids = set(master.triggers.keys()) | set(branch.triggers.keys())

    for trigger_id in all_trigger_ids:
        master_trigger: PgTrigger | None = master.triggers.get(trigger_id)
        branch_trigger: PgTrigger | None = branch.triggers.get(trigger_id)

        if master_trigger is None and branch_trigger is not None:
            # Trigger was added
            from ..changes.trigger import CreateTrigger

            changes.append(CreateTrigger(trigger=branch_trigger))
        elif master_trigger is not None and branch_trigger is None:
            # Trigger was removed
            from ..changes.trigger import DropTrigger

            changes.append(DropTrigger(trigger=master_trigger))
        elif master_trigger is not None and branch_trigger is not None:
            # Trigger exists in both - check if it changed
            if not master_trigger.semantic_equality(branch_trigger):
                # Trigger changed - need to replace it (drop + create)
                from ..changes.trigger import CreateTrigger, DropTrigger

                # Note: Triggers don't have ALTER like functions, so we drop and recreate
                changes.append(DropTrigger(trigger=master_trigger))
                changes.append(CreateTrigger(trigger=branch_trigger))

    return changes
