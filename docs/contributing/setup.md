# Contributing Setup

This guide will help you set up a development environment for contributing to pgdelta.

## Prerequisites

- Python 3.13+
- Docker (for running PostgreSQL test containers)
- Git

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/olirice/pgdelta.git
cd pgdelta
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install pgdelta in editable mode with development dependencies
pip install -e ".[dev]"

# Install documentation dependencies (optional)
pip install -e ".[docs]"
```

### 4. Install Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Test pre-commit hooks
pre-commit run --all-files
```

### 5. Verify Installation

```bash
# Run tests to verify everything works
pytest

# Run specific test categories
pytest -m "not slow"              # Skip slow tests
pytest -m integration             # Run integration tests
pytest -m roundtrip              # Run roundtrip tests

# Check code quality
mypy src/pgdelta
ruff check .
ruff format .
```

## Development Tools

### Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/pgdelta --cov-report=html

# Run tests in parallel (faster)
pytest -n auto

# Run specific test file
pytest tests/unit/test_catalog.py

# Run specific test
pytest tests/unit/test_catalog.py::test_extract_catalog_basic
```

### Code Quality

```bash
# Type checking
mypy src/pgdelta

# Linting
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Code formatting
ruff format .

# Run all pre-commit hooks
pre-commit run --all-files
```

### Documentation

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
# Visit http://localhost:8000
```

## Architecture Overview

Before contributing, familiarize yourself with pgdelta's architecture:

### Three-Phase Design
1. **Extract**: Extract schema from PostgreSQL into immutable dataclasses
2. **Diff**: Compare catalogs to generate change objects
3. **Generate**: Generate SQL DDL from change objects with dependency resolution

### Key Directories
```
src/pgdelta/
├── model/          # PostgreSQL object models
├── diff/           # Diff algorithms
├── changes/        # Change types and SQL generation
├── cli/            # Command-line interface
├── catalog.py      # Catalog extraction
└── dependency_resolution.py  # Dependency resolution
```

### Testing Philosophy
- **Real PostgreSQL**: All tests use actual PostgreSQL instances
- **Roundtrip fidelity**: Extract → Diff → Generate → Apply produces identical schemas
- **Comprehensive coverage**: 85% minimum test coverage required

## Contributing Guidelines

### Code Style

#### Python Code
- Follow PEP 8 (enforced by ruff)
- Use type hints for all functions and methods
- Write docstrings for public functions
- Use descriptive variable names

```python
# Good
def extract_catalog(session: Session) -> PgCatalog:
    """Extract complete catalog from PostgreSQL session."""
    pass

# Bad
def extract(s):
    pass
```

#### SQL Code
- Use double quotes for identifiers
- Format SQL for readability
- Include comments for complex queries

```sql
-- Good
CREATE TABLE "public"."users" (
  "id" serial PRIMARY KEY,
  "email" text NOT NULL,
  "created_at" timestamp DEFAULT now()
);

-- Bad
create table users(id serial primary key,email text not null,created_at timestamp default now());
```

### Commit Messages

Use conventional commit format:

```bash
# Feature
feat(tables): add support for partitioned tables

# Bug fix
fix(constraints): handle foreign key constraint dependencies correctly

# Documentation
docs(api): add examples for Python API usage

# Refactoring
refactor(diff): simplify table diffing algorithm

# Tests
test(integration): add roundtrip tests for complex schemas
```

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/add-partitioned-tables
   ```
3. **Make your changes**
4. **Add tests** for any new functionality
5. **Run the test suite**
   ```bash
   pytest
   mypy src/pgdelta
   ruff check .
   ```
6. **Update documentation** if needed
7. **Commit your changes**
8. **Push to your fork**
9. **Create a pull request**

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests added for new functionality
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Pre-commit hooks pass
- [ ] Commit messages follow convention

## Testing Guidelines

### Writing Tests

#### Unit Tests
Test individual components in isolation:

```python
def test_create_table_sql_generation():
    """Test CREATE TABLE SQL generation."""
    change = CreateTable(
        stable_id="t:public.users",
        namespace="public",
        relname="users",
        columns=[
            PgAttribute(attname="id", type_name="integer", attnotnull=True),
        ]
    )
    
    sql = generate_create_table_sql(change)
    assert "CREATE TABLE \"public\".\"users\"" in sql
    assert "\"id\" integer NOT NULL" in sql
```

#### Integration Tests
Test with real PostgreSQL:

```python
def test_table_creation_roundtrip(postgres_session):
    """Test table creation roundtrip fidelity."""
    # Create table
    postgres_session.execute(text("""
        CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        )
    """))
    postgres_session.commit()
    
    # Extract catalog
    catalog = extract_catalog(postgres_session)
    
    # Verify table exists
    assert "t:public.test_table" in catalog.classes
    
    # Verify columns
    table = catalog.classes["t:public.test_table"]
    columns = catalog.get_class_attributes(table.stable_id)
    assert len(columns) == 2
    assert columns[0].attname == "id"
    assert columns[1].attname == "name"
```

#### Roundtrip Tests
Test complete workflows:

```python
def test_complex_schema_roundtrip(postgres_session):
    """Test roundtrip fidelity with complex schema."""
    # Create complex schema
    setup_complex_schema(postgres_session)
    
    # Extract original catalog
    original_catalog = extract_catalog(postgres_session)
    
    # Generate changes to recreate schema
    empty_catalog = create_empty_catalog()
    changes = empty_catalog.diff(original_catalog)
    
    # Apply changes to empty database
    apply_changes_to_empty_database(changes)
    
    # Extract final catalog
    final_catalog = extract_catalog(empty_postgres_session)
    
    # Verify catalogs are semantically identical
    assert original_catalog.semantically_equals(final_catalog)
```

### Test Organization

```
tests/
├── unit/              # Unit tests
│   ├── test_catalog.py
│   ├── test_diff.py
│   └── test_sql_generation.py
├── integration/       # Integration tests
│   ├── test_extract.py
│   ├── test_roundtrip.py
│   └── test_dependency_resolution.py
├── cli/              # CLI tests
│   └── test_main.py
└── conftest.py       # Test fixtures
```

### Test Fixtures

```python
# conftest.py
@pytest.fixture
def postgres_container():
    """PostgreSQL test container."""
    with PostgresContainer("postgres:17") as container:
        yield container

@pytest.fixture
def postgres_session(postgres_container):
    """PostgreSQL session for testing."""
    engine = create_engine(postgres_container.get_connection_url())
    with Session(engine) as session:
        yield session

@pytest.fixture
def empty_catalog():
    """Empty catalog for testing."""
    return PgCatalog(
        namespaces={},
        classes={},
        attributes={},
        constraints={},
        indexes={},
        sequences={},
        policies={},
        procedures={},
        triggers={},
        types={},
        depends=[],
    )
```

## Documentation Guidelines

### Code Documentation

#### Docstrings
Use Google-style docstrings:

```python
def generate_sql(change: DDL) -> str:
    """Generate SQL DDL from a change object.
    
    Args:
        change: The change object to generate SQL for.
        
    Returns:
        SQL DDL statement as a string.
        
    Raises:
        NotImplementedError: If the change type is not supported.
        
    Example:
        >>> change = CreateTable(stable_id="t:public.users", ...)
        >>> sql = generate_sql(change)
        >>> print(sql)
        CREATE TABLE "public"."users" (...);
    """
```

#### Type Hints
Use comprehensive type hints:

```python
from typing import Dict, List, Optional, Union

def diff_objects(
    master_objects: dict[str, T],
    branch_objects: dict[str, T],
    create_fn: Callable[[T], DDL],
    drop_fn: Callable[[T], DDL],
) -> list[DDL]:
    """Diff two object collections."""
    pass
```

### Documentation Files

#### Structure
- Use clear headings and sections
- Include code examples
- Add links to related documentation
- Keep examples up-to-date

#### Examples
Include practical examples:

```python
# Good - practical example
from pgdelta import extract_catalog, generate_sql

# Extract catalogs
source_catalog = extract_catalog(source_session)
target_catalog = extract_catalog(target_session)

# Generate changes
changes = source_catalog.diff(target_catalog)

# Generate SQL
sql_statements = [generate_sql(change) for change in changes]
```

## Debugging

### Common Issues

#### Test Failures
```bash
# Run failed tests with verbose output
pytest -v --tb=short

# Run specific failed test
pytest tests/unit/test_catalog.py::test_extract_catalog_basic -v

# Run tests with pdb on failure
pytest --pdb
```

#### Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall in editable mode
pip install -e ".[dev]"
```

#### Docker Issues
```bash
# Check Docker is running
docker ps

# Pull PostgreSQL image
docker pull postgres:17

# Clean up containers
docker container prune
```

### Debugging Tools

#### pytest
```bash
# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src/pgdelta --cov-report=html

# Run specific markers
pytest -m integration
pytest -m "not slow"
```

#### mypy
```bash
# Check specific file
mypy src/pgdelta/catalog.py

# Check with verbose output
mypy --verbose src/pgdelta/

# Generate HTML report
mypy --html-report mypy-report src/pgdelta/
```

#### ruff
```bash
# Check specific file
ruff check src/pgdelta/catalog.py

# Auto-fix issues
ruff check --fix .

# Show all rules
ruff linter
```

## Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code review and collaboration

### Resources
- [Architecture Documentation](../architecture.md)
- [API Documentation](../api/python.md)
- [Supported Entities](../entities/overview.md)
- [Dependency Resolution](../dependency-resolution.md)

### Asking Questions
When asking for help:
1. Describe what you're trying to do
2. Include relevant code snippets
3. Provide error messages
4. Share your environment details
5. Mention what you've already tried

## License

By contributing to pgdelta, you agree that your contributions will be licensed under the Apache 2.0 License.

## Recognition

Contributors are recognized in:
- GitHub contributor list
- Release notes
- Documentation acknowledgments

Thank you for contributing to pgdelta!