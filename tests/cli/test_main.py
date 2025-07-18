"""Tests for CLI main module."""

import re
import subprocess
import sys

import pytest


def strip_ansi_codes(text: str) -> str:
    """Strip ANSI color codes from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@pytest.mark.cli
def test_cli_help():
    """Test that CLI help output works."""
    result = subprocess.run(
        [sys.executable, "-m", "pgdelta.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Strip ANSI codes from output to avoid CI issues
    clean_output = strip_ansi_codes(result.stdout)

    assert "PostgreSQL schema differ and DDL generator" in clean_output
    assert "diff-headless" in clean_output
    assert "info" in clean_output


@pytest.mark.cli
def test_cli_version():
    """Test that CLI version output works."""
    result = subprocess.run(
        [sys.executable, "-m", "pgdelta.cli.main", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Strip ANSI codes from output to avoid CI issues
    clean_output = strip_ansi_codes(result.stdout)

    assert "pgdelta version" in clean_output


@pytest.mark.cli
def test_info_command():
    """Test the info command."""
    result = subprocess.run(
        [sys.executable, "-m", "pgdelta.cli.main", "info"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Strip ANSI codes from output to avoid CI issues
    clean_output = strip_ansi_codes(result.stdout)

    assert "pgdelta Information" in clean_output
    assert "Version" in clean_output
    assert "Python Version" in clean_output
    assert "System Information" in clean_output
    assert "Operating System" in clean_output


@pytest.mark.cli
def test_diff_headless_help():
    """Test diff-headless command help."""
    result = subprocess.run(
        [sys.executable, "-m", "pgdelta.cli.main", "diff-headless", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Strip ANSI codes from output to avoid CI issues
    clean_output = strip_ansi_codes(result.stdout)

    assert (
        "Generate diff between schemas using isolated Docker containers" in clean_output
    )
    assert "--master-sql" in clean_output
    assert "--branch-sql" in clean_output
    assert "--initial-sql" in clean_output


@pytest.mark.cli
def test_diff_headless_empty_schemas():
    """Test diff-headless with empty schemas (no parameters)."""
    result = subprocess.run(
        [sys.executable, "-m", "pgdelta.cli.main", "diff-headless"],
        capture_output=True,
        text=True,
        timeout=180,  # Allow time for container startup
    )
    assert result.returncode == 0
    assert "No changes detected between schemas" in result.stdout


@pytest.mark.cli
def test_diff_headless_empty_master_with_branch():
    """Test diff-headless with empty master and populated branch."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            "",
            "--branch-sql",
            "CREATE TABLE test (id SERIAL PRIMARY KEY);",
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    assert 'CREATE TABLE "public"."test"' in result.stdout


@pytest.mark.cli
def test_diff_headless_with_schema_changes():
    """Test diff-headless with actual schema differences."""
    master_sql = "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(50));"
    branch_sql = """
        CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100), email TEXT);
        CREATE TABLE posts (id SERIAL PRIMARY KEY, title TEXT, user_id INTEGER REFERENCES users(id));
    """

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            master_sql,
            "--branch-sql",
            branch_sql,
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    # Should detect differences and generate CREATE statements to add new features
    assert "CREATE TABLE" in result.stdout  # Should create posts table
    assert "ALTER TABLE" in result.stdout  # Should modify users table
    assert "Generated" in result.stdout


@pytest.mark.cli
def test_diff_headless_with_initial_sql():
    """Test diff-headless with initial SQL setup."""
    initial_sql = (
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE SCHEMA IF NOT EXISTS app;'
    )
    master_sql = (
        "CREATE TABLE app.test (id UUID PRIMARY KEY DEFAULT uuid_generate_v4());"
    )
    branch_sql = "CREATE TABLE app.test (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), name TEXT);"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--initial-sql",
            initial_sql,
            "--master-sql",
            master_sql,
            "--branch-sql",
            branch_sql,
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    # Should work without errors when using extensions and schemas


@pytest.mark.cli
def test_diff_headless_output_to_file(tmp_path):
    """Test diff-headless with output to file."""
    output_file = tmp_path / "migration.sql"

    # Use schemas that will definitely produce differences
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            "",
            "--branch-sql",
            "CREATE TABLE test (id SERIAL PRIMARY KEY, name TEXT);",
            "--output",
            str(output_file),
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0

    # Check that file was created and contains SQL
    assert output_file.exists()
    content = output_file.read_text()
    # Should contain CREATE statement for the table
    assert "CREATE TABLE" in content


@pytest.mark.cli
def test_diff_headless_verbose_mode():
    """Test diff-headless with verbose output."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            "CREATE TABLE test (id INT);",
            "--branch-sql",
            "",
            "--verbose",
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    assert "Using PostgreSQL image:" in result.stdout
    assert "Creating temporary PostgreSQL container..." in result.stdout


@pytest.mark.cli
def test_diff_headless_custom_postgres_image():
    """Test diff-headless with custom PostgreSQL image."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--postgres-image",
            "postgres:16",
            "--verbose",
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    assert "postgres:16" in result.stdout


@pytest.mark.cli
def test_diff_headless_invalid_sql():
    """Test diff-headless with invalid SQL should fail gracefully."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            "INVALID SQL STATEMENT",
            "--branch-sql",
            "",
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    # Should exit with error code and show error message
    assert result.returncode != 0
    assert "Error:" in result.stdout or "Error:" in result.stderr


@pytest.mark.cli
def test_diff_headless_verbose_with_initial_sql():
    """Test diff-headless with verbose mode and initial SQL to cover progress update."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--initial-sql",
            "CREATE EXTENSION IF NOT EXISTS btree_gin;",
            "--master-sql",
            "",
            "--branch-sql",
            "",
            "--verbose",
            "--no-verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    # Check for any verbose output (actual message might vary)
    assert "PostgreSQL image:" in result.stdout


@pytest.mark.cli
def test_diff_headless_with_verification_success():
    """Test diff-headless with verification that succeeds."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            "",
            "--branch-sql",
            "",
            "--verify",  # Enable verification
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    # Just check that it runs successfully with verification enabled


@pytest.mark.cli
def test_diff_headless_with_verification_and_changes():
    """Test diff-headless with verification and actual changes."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pgdelta.cli.main",
            "diff-headless",
            "--master-sql",
            "CREATE TABLE test1 (id INT);",
            "--branch-sql",
            "CREATE TABLE test2 (id INT);",  # Different table name
            "--verify",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0
    # Just check that it runs successfully with verification enabled
