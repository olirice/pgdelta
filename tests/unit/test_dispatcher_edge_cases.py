"""Unit tests for dispatcher edge cases."""

import pytest

from pgdelta.changes.dispatcher import assert_never, generate_sql


def test_assert_never():
    """Test assert_never function."""
    with pytest.raises(AssertionError, match="Unhandled value: invalid_value"):
        assert_never("invalid_value")


def test_generate_sql_with_invalid_change_type():
    """Test generate_sql with invalid change type."""

    # This would normally be caught by type checkers, but we can test runtime behavior
    class InvalidChange:
        pass

    invalid_change = InvalidChange()

    with pytest.raises(AssertionError, match="Unhandled value"):
        generate_sql(invalid_change)  # type: ignore
