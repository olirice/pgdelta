"""Sequence diff logic."""

from ..catalog import PgCatalog
from ..changes import DDL
from ..changes.sequence import AlterSequence, CreateSequence, DropSequence


def diff_sequences(master: PgCatalog, branch: PgCatalog) -> list[DDL]:
    """Diff sequences between catalogs."""
    changes: list[DDL] = []

    all_sequence_ids = set(master.sequences.keys()) | set(branch.sequences.keys())

    for sequence_id in all_sequence_ids:
        master_sequence = master.sequences.get(sequence_id)
        branch_sequence = branch.sequences.get(sequence_id)

        match (master_sequence, branch_sequence):
            case (None, branch_sequence) if branch_sequence is not None:
                # Create new sequence
                changes.append(
                    CreateSequence(
                        stable_id=branch_sequence.stable_id,
                        sequence=branch_sequence,
                    )
                )
            case (master_sequence, None) if master_sequence is not None:
                # Drop sequence
                changes.append(
                    DropSequence(
                        stable_id=master_sequence.stable_id,
                        namespace=master_sequence.namespace,
                        seqname=master_sequence.seqname,
                    )
                )
            case (master_sequence, branch_sequence) if (
                master_sequence is not None and branch_sequence is not None
            ):
                # Check if sequences are different (ignoring current value)
                if not master_sequence.semantic_equality(branch_sequence):
                    changes.append(
                        AlterSequence(
                            stable_id=branch_sequence.stable_id,
                            old_sequence=master_sequence,
                            new_sequence=branch_sequence,
                        )
                    )

    return changes
