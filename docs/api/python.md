# Python API

pgdelta provides a Python API for programmatic schema diffing and DDL generation.

## Installation

```bash
pip install pgdelta
```

## Basic Usage

```python
from pgdelta import PgCatalog, generate_sql
from pgdelta.catalog import extract_catalog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Connect to databases
source_engine = create_engine("postgresql://user:pass@localhost/source_db")
target_engine = create_engine("postgresql://user:pass@localhost/target_db")

with Session(source_engine) as source_session, Session(target_engine) as target_session:
    # Extract schemas
    source_catalog = extract_catalog(source_session)
    target_catalog = extract_catalog(target_session)

    # Generate migration from target to source
    changes = target_catalog.diff(source_catalog)

    # Generate SQL statements
    sql_statements = [generate_sql(change) for change in changes]

    for sql in sql_statements:
        print(sql)
```

## API Reference

### Core Functions

::: pgdelta.catalog.extract_catalog

### Classes

::: pgdelta.PgCatalog

### Functions

::: pgdelta.generate_sql

### Exceptions

::: pgdelta.PgDeltaError

::: pgdelta.DependencyResolutionError

::: pgdelta.CyclicDependencyError

## Advanced Usage

### Custom Connection Handling

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pgdelta.catalog import extract_catalog

def extract_from_database(connection_string: str) -> PgCatalog:
    """Extract catalog from a database connection string."""
    engine = create_engine(connection_string)
    with Session(engine) as session:
        return extract_catalog(session)

# Usage
source_catalog = extract_from_database("postgresql://user:pass@localhost/db1")
target_catalog = extract_from_database("postgresql://user:pass@localhost/db2")
```

### Filtering Changes

```python
from pgdelta.changes import CreateTable, DropTable

# Extract catalogs
source_catalog = extract_catalog(source_session)
target_catalog = extract_catalog(target_session)

# Get all changes
all_changes = target_catalog.diff(source_catalog)

# Filter only table creation changes
table_creates = [change for change in all_changes if isinstance(change, CreateTable)]

# Filter only table drops
table_drops = [change for change in all_changes if isinstance(change, DropTable)]

# Generate SQL for specific changes
create_sql = [generate_sql(change) for change in table_creates]
```

### Semantic Equality Checking

```python
# Check if two catalogs are semantically identical
if source_catalog.semantically_equals(target_catalog):
    print("Schemas are identical")
else:
    print("Schemas differ")
    changes = source_catalog.diff(target_catalog)
    print(f"Found {len(changes)} changes")
```

### Working with Individual Models

```python
from pgdelta.model import PgClass, PgAttribute

# Access individual tables
for table in source_catalog.tables:
    print(f"Table: {table.schema}.{table.name}")
    
    # Access columns
    for column in table.columns:
        print(f"  Column: {column.name} ({column.type_name})")
        
        # Check column properties
        if not column.is_nullable:
            print(f"    NOT NULL")
        if column.has_default:
            print(f"    DEFAULT {column.default}")
```

### Error Handling

```python
from pgdelta import DependencyResolutionError, CyclicDependencyError

try:
    changes = source_catalog.diff(target_catalog)
    sql_statements = [generate_sql(change) for change in changes]
    
except DependencyResolutionError as e:
    print(f"Could not resolve dependencies: {e}")
    
except CyclicDependencyError as e:
    print(f"Cyclic dependency detected: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Integration Examples

### Flask Application

```python
from flask import Flask, request, jsonify
from pgdelta import extract_catalog, generate_sql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

app = Flask(__name__)

@app.route('/diff', methods=['POST'])
def generate_diff():
    """Generate schema diff between two databases."""
    data = request.json
    source_url = data['source_url']
    target_url = data['target_url']
    
    try:
        source_engine = create_engine(source_url)
        target_engine = create_engine(target_url)
        
        with Session(source_engine) as source_session, \
             Session(target_engine) as target_session:
            
            source_catalog = extract_catalog(source_session)
            target_catalog = extract_catalog(target_session)
            
            changes = source_catalog.diff(target_catalog)
            sql_statements = [generate_sql(change) for change in changes]
            
            return jsonify({
                'success': True,
                'sql': sql_statements,
                'change_count': len(changes)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Django Management Command

```python
from django.core.management.base import BaseCommand
from django.db import connection
from pgdelta.catalog import extract_catalog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

class Command(BaseCommand):
    help = 'Generate schema diff'

    def add_arguments(self, parser):
        parser.add_argument('--target-url', required=True)
        parser.add_argument('--output', required=False)

    def handle(self, *args, **options):
        # Use Django's database connection for source
        django_url = f"postgresql://{connection.settings_dict['USER']}:" \
                    f"{connection.settings_dict['PASSWORD']}@" \
                    f"{connection.settings_dict['HOST']}:" \
                    f"{connection.settings_dict['PORT']}/" \
                    f"{connection.settings_dict['NAME']}"
        
        source_engine = create_engine(django_url)
        target_engine = create_engine(options['target_url'])
        
        with Session(source_engine) as source_session, \
             Session(target_engine) as target_session:
            
            source_catalog = extract_catalog(source_session)
            target_catalog = extract_catalog(target_session)
            
            changes = source_catalog.diff(target_catalog)
            
            if not changes:
                self.stdout.write("No changes detected")
                return
            
            sql_statements = [generate_sql(change) for change in changes]
            
            if options['output']:
                with open(options['output'], 'w') as f:
                    f.write('\n'.join(sql_statements))
                self.stdout.write(f"Wrote {len(sql_statements)} statements to {options['output']}")
            else:
                for sql in sql_statements:
                    self.stdout.write(sql)
```

### Async Usage

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from pgdelta.catalog import extract_catalog

async def async_diff():
    """Example of using pgdelta with async SQLAlchemy."""
    
    # Note: extract_catalog currently requires sync sessions
    # This is a pattern for working with async engines
    
    source_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db1")
    target_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db2")
    
    # Convert to sync for extraction
    source_sync = source_engine.sync_engine
    target_sync = target_engine.sync_engine
    
    with Session(source_sync) as source_session, \
         Session(target_sync) as target_session:
        
        source_catalog = extract_catalog(source_session)
        target_catalog = extract_catalog(target_session)
        
        changes = source_catalog.diff(target_catalog)
        sql_statements = [generate_sql(change) for change in changes]
        
        return sql_statements

# Usage
async def main():
    statements = await async_diff()
    for sql in statements:
        print(sql)

asyncio.run(main())
```

## Testing

### Unit Testing with pytest

```python
import pytest
from pgdelta import PgCatalog, generate_sql
from pgdelta.catalog import extract_catalog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

@pytest.fixture
def postgres_container():
    """Pytest fixture providing a PostgreSQL container."""
    with PostgresContainer("postgres:17") as container:
        yield container

def test_table_creation_diff(postgres_container):
    """Test that table creation is detected correctly."""
    
    # Get connection URL
    url = postgres_container.get_connection_url()
    engine = create_engine(url)
    
    with Session(engine) as session:
        # Create initial schema
        session.execute(text("CREATE SCHEMA test"))
        session.commit()
        
        # Extract empty catalog
        empty_catalog = extract_catalog(session)
        
        # Add a table
        session.execute(text("""
            CREATE TABLE test.users (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL
            )
        """))
        session.commit()
        
        # Extract catalog with table
        table_catalog = extract_catalog(session)
        
        # Generate diff
        changes = empty_catalog.diff(table_catalog)
        
        # Should have one CREATE TABLE change
        assert len(changes) == 1
        assert "CREATE TABLE" in generate_sql(changes[0])
        assert "test" in generate_sql(changes[0])
        assert "users" in generate_sql(changes[0])
```

### Integration Testing

```python
from pgdelta.catalog import extract_catalog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

def test_roundtrip_fidelity():
    """Test that Extract → Diff → Generate → Apply produces identical schemas."""
    
    # Setup two identical databases
    source_engine = create_engine("postgresql://user:pass@localhost/source")
    target_engine = create_engine("postgresql://user:pass@localhost/target")
    
    with Session(source_engine) as source_session, \
         Session(target_engine) as target_session:
        
        # Apply initial schema to source
        source_session.execute(text("""
            CREATE SCHEMA app;
            CREATE TABLE app.users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL
            );
        """))
        source_session.commit()
        
        # Extract catalogs
        source_catalog = extract_catalog(source_session)
        target_catalog = extract_catalog(target_session)
        
        # Generate migration
        changes = target_catalog.diff(source_catalog)
        sql_statements = [generate_sql(change) for change in changes]
        
        # Apply migration to target
        for sql in sql_statements:
            target_session.execute(text(sql))
        target_session.commit()
        
        # Extract final catalog
        final_catalog = extract_catalog(target_session)
        
        # Should be semantically identical
        assert source_catalog.semantically_equals(final_catalog)
```

## Performance Considerations

### Large Schema Handling

```python
# For very large schemas, consider extracting only specific schemas
from pgdelta.catalog import extract_catalog

# Extract only specific schemas (not yet implemented, but planned)
# catalog = extract_catalog(session, schema_filter=['public', 'app'])

# Current approach - extract all and filter
catalog = extract_catalog(session)
filtered_tables = [t for t in catalog.tables if t.schema in ['public', 'app']]
```

## Best Practices

1. **Use context managers** for database connections
2. **Handle exceptions** appropriately for production code
3. **Test with real databases** using testcontainers
4. **Validate generated SQL** before applying to production
5. **Use semantic equality** to verify migrations
6. **Filter changes** when you only need specific types
7. **Test with representative data** before production use