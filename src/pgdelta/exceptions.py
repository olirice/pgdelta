"""
Custom exceptions for pgdelta.

This module provides a hierarchy of exceptions used throughout the pgdelta
package to provide more specific error handling and better error messages.
"""


class PgDeltaError(Exception):
    """
    Base exception class for all pgdelta-specific exceptions.

    This serves as the root of the exception hierarchy and allows users
    to catch all pgdelta-related exceptions with a single except clause.
    """

    pass


class DependencyResolutionError(PgDeltaError):
    """
    Exception raised when dependency resolution fails.

    This exception is raised when the dependency resolver encounters
    an unresolvable situation, such as cyclic dependencies between
    database objects.
    """

    pass


class CyclicDependencyError(DependencyResolutionError):
    """
    Exception raised when a cyclic dependency is detected.

    This specific exception is raised when the dependency resolver
    detects a cycle in the dependency graph that cannot be resolved
    through standard topological sorting.
    """

    def __init__(self, message: str = "Cyclic dependency detected in DDL operations"):
        """
        Initialize the cyclic dependency error.

        Args:
            message: Custom error message describing the cyclic dependency
        """
        super().__init__(message)
        self.message = message
