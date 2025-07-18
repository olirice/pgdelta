#!/usr/bin/env python3
"""Architecture compliance checker for pgdelta."""

import ast
import sys
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """Architecture violation."""

    file: str
    line: int
    message: str


class ArchitectureChecker(ast.NodeVisitor):
    """Check for architecture compliance violations."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Check function calls for forbidden patterns."""
        if isinstance(node.func, ast.Name) and node.func.id in {"hasattr"}:
            self.violations.append(
                Violation(
                    file=self.file_path,
                    line=node.lineno,
                    message=f"Forbidden function: {node.func.id}()",
                )
            )

        # Check for hardcoded schema names
        if (
            isinstance(node.func, ast.Attribute)
            and hasattr(node.func.value, "id")
            and node.func.value.id == "str"
        ):
            # Check string literals for hardcoded 'public' schema
            for arg in node.args:
                if isinstance(arg, ast.Constant) and arg.value == "public":
                    self.violations.append(
                        Violation(
                            file=self.file_path,
                            line=node.lineno,
                            message="Hardcoded 'public' schema name",
                        )
                    )

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        """Check string constants for forbidden patterns."""
        if (
            isinstance(node.value, str)
            and node.value.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE"))
            and "changes/" not in self.file_path
        ):
            self.violations.append(
                Violation(
                    file=self.file_path,
                    line=node.lineno,
                    message="Raw SQL in core logic (should be in changes/ module)",
                )
            )

        self.generic_visit(node)


def check_file(file_path: Path) -> list[Violation]:
    """Check a single Python file for architecture violations."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())

        checker = ArchitectureChecker(str(file_path))
        checker.visit(tree)
        return checker.violations
    except Exception as e:
        return [Violation(file=str(file_path), line=0, message=f"Parse error: {e}")]


def main() -> None:
    """Main entry point."""
    src_dir = Path("src/pgdelta")
    if not src_dir.exists():
        print("No src/pgdelta directory found")
        return

    all_violations = []
    for py_file in src_dir.rglob("*.py"):
        violations = check_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        print("Architecture violations found:")
        for violation in all_violations:
            print(f"  {violation.file}:{violation.line}: {violation.message}")
        sys.exit(1)
    else:
        print("No architecture violations found")


if __name__ == "__main__":
    main()
