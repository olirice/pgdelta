"""
Test configuration and fixtures for pgdelta tests.

This module provides pytest fixtures for database testing using testcontainers
}ith PostgreSQL. It includes setup for connection management and transaction
isolation to ensure tests can run in parallel.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

# Mock classids for testing (typical PostgreSQL system catalog OIDs)
MOCK_CLASSIDS = {
    "pg_namespace": 2615,
    "pg_class": 1259,
    "pg_attribute": 1249,
    "pg_type": 1247,
    "pg_proc": 1255,
}


@pytest.fixture
def mock_classids():
    """Provide mock classids for testing."""
    return MOCK_CLASSIDS


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """
    Session-scoped PostgreSQL container for all tests.

    Uses testcontainers to spin up a real PostgreSQL instance for testing.
    This ensures our tests run against actual PostgreSQL system catalogs.
    """
    with PostgresContainer("postgres:17") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    """Get the database URL for the test PostgreSQL instance."""
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def alt_database_url(postgres_container: PostgresContainer) -> str:
    """Get the database URL for the alternate test database."""
    # Create a second database in the same cluster for roundtrip testing
    import psycopg2

    # Connect to the default database to create the alternate one
    conn_url = postgres_container.get_connection_url()
    if "+psycopg2" in conn_url:
        conn_url = conn_url.replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(conn_url)
    conn.autocommit = True

    try:
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE pgdelta_alt_test")
        cursor.close()
    except psycopg2.errors.DuplicateDatabase:
        # Database already exists, that's fine
        pass
    finally:
        conn.close()

    # Return URL pointing to the alternate database
    base_url = postgres_container.get_connection_url()
    # Replace the database name in the URL
    return base_url.rsplit("/", 1)[0] + "/pgdelta_alt_test"


@pytest.fixture(scope="session")
def engine(database_url: str):
    """SQLAlchemy engine for the test database."""
    return create_engine(database_url)


@pytest.fixture(scope="session")
def alt_engine(alt_database_url: str):
    """SQLAlchemy engine for the alternate test database."""
    return create_engine(alt_database_url)


@pytest.fixture
def session(engine):
    """
    Create a database session with transaction rollback for test isolation.

    Each test gets a fresh transaction that is rolled back at the end,
    ensuring tests don't interfere with each other.
    """
    connection = engine.connect()
    transaction = connection.begin()

    # Create SQLAlchemy session bound to the connection
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def alt_session(alt_engine):
    """
    Create an alternate database session for roundtrip testing.

    This session connects to a separate database in the same PostgreSQL cluster,
    allowing for clean equivalence testing without schema manipulation.
    """
    connection = alt_engine.connect()
    transaction = connection.begin()

    # Create SQLAlchemy session bound to the connection
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def master_session(engine):
    """
    Create a master database session with transaction rollback for test isolation.

    Each test gets a fresh transaction that is rolled back at the end,
    ensuring tests don't interfere with each other.
    """
    connection = engine.connect()
    transaction = connection.begin()

    # Create SQLAlchemy session bound to the connection
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def branch_session(alt_engine):
    """
    Create a branch database session for roundtrip testing.

    This session connects to a separate database in the same PostgreSQL cluster,
    allowing for clean equivalence testing without schema manipulation.
    """
    connection = alt_engine.connect()
    transaction = connection.begin()

    # Create SQLAlchemy session bound to the connection
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
