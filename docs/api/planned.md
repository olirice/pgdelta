# Planned API

This document outlines the planned API features for future versions of pgdelta.

## HTTP API (Not Implemented)

A REST API for schema diffing and DDL generation.

### Server Configuration

```python
from pgdelta.server import PgDeltaServer

# Start server with configuration
server = PgDeltaServer(
    host="0.0.0.0",
    port=8080,
    max_connections=100,
    timeout=30
)

server.start()
```

### API Endpoints

#### `POST /diff`

Generate schema diff between two databases.

**Request:**
```json
{
  "source": {
    "connection_string": "postgresql://user:pass@host:5432/source_db",
    "schema_filter": ["public", "app"]
  },
  "target": {
    "connection_string": "postgresql://user:pass@host:5432/target_db",
    "schema_filter": ["public", "app"]
  },
  "options": {
    "verify": true,
    "include_drops": true,
    "format": "sql"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "changes": [
    {
      "type": "CREATE_TABLE",
      "object": "public.users",
      "sql": "CREATE TABLE \"public\".\"users\" (\"id\" serial PRIMARY KEY);"
    }
  ],
  "summary": {
    "total_changes": 1,
    "creates": 1,
    "drops": 0,
    "alters": 0
  },
  "verification": {
    "passed": true,
    "roundtrip_fidelity": true
  }
}
```

#### `POST /diff/sql`

Generate diff using SQL statements instead of database connections.

**Request:**
```json
{
  "source_sql": "CREATE TABLE users (id SERIAL PRIMARY KEY);",
  "target_sql": "CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT);",
  "initial_sql": "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
  "options": {
    "postgres_version": "17",
    "verify": true
  }
}
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.4.0",
  "uptime": "2h 15m 30s"
}
```

#### `GET /info`

System information endpoint.

**Response:**
```json
{
  "version": "0.4.0",
  "supported_postgres_versions": ["13", "14", "15", "16", "17"],
  "supported_entities": [
    "schemas", "tables", "indexes", "constraints",
    "views", "functions", "triggers", "sequences"
  ],
  "system": {
    "python_version": "3.13.0",
    "os": "Linux",
    "memory_mb": 2048
  }
}
```

## Enhanced Python API (Not Implemented)

### Async Support

```python
from pgdelta.async_catalog import extract_catalog_async
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

async def async_diff():
    source_engine = create_async_engine("postgresql+asyncpg://...")
    target_engine = create_async_engine("postgresql+asyncpg://...")

    async with AsyncSession(source_engine) as source_session, \
               AsyncSession(target_engine) as target_session:

        source_catalog = await extract_catalog_async(source_session)
        target_catalog = await extract_catalog_async(target_session)

        changes = await source_catalog.diff_async(target_catalog)
        return changes
```

### Streaming API

```python
from pgdelta.streaming import stream_changes

# Stream changes as they're generated (useful for large schemas)
async for change in stream_changes(source_catalog, target_catalog):
    sql = generate_sql(change)
    print(sql)
```

### Schema Filtering

```python
from pgdelta.catalog import extract_catalog

# Extract only specific schemas
catalog = extract_catalog(
    session,
    schema_filter=['public', 'app'],
    exclude_system_objects=True
)

# Extract only specific object types
catalog = extract_catalog(
    session,
    object_filter=['tables', 'indexes', 'constraints']
)
```

### Change Batching

```python
from pgdelta.batching import batch_changes

# Group changes into logical batches
changes = source_catalog.diff(target_catalog)
batches = batch_changes(changes, strategy='dependencies')

for batch in batches:
    print(f"Batch {batch.id}: {len(batch.changes)} changes")
    for change in batch.changes:
        print(f"  - {generate_sql(change)}")
```

### Custom Change Handlers

```python
from pgdelta.handlers import ChangeHandler

class CustomTableHandler(ChangeHandler):
    def handle_create_table(self, change: CreateTable) -> str:
        # Custom SQL generation logic
        sql = f"CREATE TABLE {change.table.full_name} ("
        # ... custom logic
        return sql

# Register custom handler
catalog.register_handler(CustomTableHandler())
```

## Configuration API (Not Implemented)

### YAML Configuration

```yaml
# pgdelta.yml
pgdelta:
  version: "0.2.0"

  databases:
    source:
      connection_string: "postgresql://user:pass@localhost/source"
      schema_filter: ["public", "app"]

    target:
      connection_string: "postgresql://user:pass@localhost/target"
      schema_filter: ["public", "app"]

  options:
    verify: true
    include_drops: true
    dependency_resolution: "strict"

  output:
    format: "sql"
    file: "migration.sql"

  logging:
    level: "INFO"
    file: "pgdelta.log"
```

### Configuration Loading

```python
from pgdelta.config import load_config

# Load from YAML file
config = load_config("pgdelta.yml")

# Generate diff using configuration
changes = config.generate_diff()
```

## Plugin System (Not Implemented)

### Custom Entity Support

```python
from pgdelta.plugins import EntityPlugin

class CustomExtensionPlugin(EntityPlugin):
    entity_type = "extension"

    def extract(self, session):
        # Extract custom entity data
        pass

    def diff(self, source, target):
        # Generate changes for custom entity
        pass

    def generate_sql(self, change):
        # Generate SQL for custom entity
        pass

# Register plugin
pgdelta.register_plugin(CustomExtensionPlugin())
```

### Pre/Post Hooks

```python
from pgdelta.hooks import PreDiffHook, PostDiffHook

class ValidationHook(PreDiffHook):
    def execute(self, source_catalog, target_catalog):
        # Validate schemas before diffing
        if not self.validate_schemas(source_catalog, target_catalog):
            raise ValueError("Schema validation failed")

class NotificationHook(PostDiffHook):
    def execute(self, changes):
        # Send notifications after diff generation
        if len(changes) > 10:
            self.send_alert(f"Large migration detected: {len(changes)} changes")

# Register hooks
pgdelta.register_hook(ValidationHook())
pgdelta.register_hook(NotificationHook())
```

## Advanced Features (Not Implemented)

### Schema Versioning

```python
from pgdelta.versioning import SchemaVersion

# Track schema versions
version = SchemaVersion.create(catalog, version="1.2.0", description="Added user tables")

# Generate migration between versions
migration = SchemaVersion.diff("1.1.0", "1.2.0")
```

### Rollback Generation

```python
from pgdelta.rollback import generate_rollback

# Generate rollback script
changes = source_catalog.diff(target_catalog)
rollback_changes = generate_rollback(changes)
rollback_sql = [generate_sql(change) for change in rollback_changes]
```

### Migration Simulation

```python
from pgdelta.simulation import simulate_migration

# Simulate migration without applying
result = simulate_migration(
    source_catalog=source_catalog,
    target_catalog=target_catalog,
    validate=True
)

print(f"Migration would create {result.creates} objects")
print(f"Migration would drop {result.drops} objects")
print(f"Estimated duration: {result.estimated_duration}")
```

### Parallel Processing

```python
from pgdelta.parallel import ParallelDiffer

# Process large schemas in parallel
differ = ParallelDiffer(workers=4)
changes = await differ.diff_async(source_catalog, target_catalog)
```

## GraphQL API (Not Implemented)

### Schema

```graphql
type Query {
  diff(source: DatabaseInput!, target: DatabaseInput!): DiffResult!
  catalog(database: DatabaseInput!): Catalog!
  health: HealthStatus!
}

type Mutation {
  generateMigration(input: MigrationInput!): MigrationResult!
  applyMigration(input: ApplyMigrationInput!): ApplyResult!
}

type DiffResult {
  changes: [Change!]!
  summary: DiffSummary!
  verification: VerificationResult!
}

type Change {
  type: ChangeType!
  object: String!
  sql: String!
  dependencies: [String!]!
}

enum ChangeType {
  CREATE_TABLE
  DROP_TABLE
  ALTER_TABLE
  CREATE_INDEX
  DROP_INDEX
  CREATE_CONSTRAINT
  DROP_CONSTRAINT
}
```

### Usage

```graphql
query GetDiff($source: DatabaseInput!, $target: DatabaseInput!) {
  diff(source: $source, target: $target) {
    changes {
      type
      object
      sql
    }
    summary {
      totalChanges
      creates
      drops
      alters
    }
    verification {
      passed
      roundtripFidelity
    }
  }
}
```

## Monitoring & Observability (Not Implemented)

### Metrics Collection

```python
from pgdelta.metrics import MetricsCollector

collector = MetricsCollector()

# Custom metrics
collector.gauge("catalog_size", len(catalog.tables))
collector.counter("diff_operations").increment()
collector.histogram("diff_duration", duration)

# Export to Prometheus
collector.export_prometheus("/metrics")
```

### Tracing

```python
from pgdelta.tracing import trace

@trace("extract_catalog")
def extract_catalog(session):
    with trace("query_pg_class"):
        tables = session.query(PgClass).all()
    return catalog
```

### Logging

```python
from pgdelta.logging import get_logger

logger = get_logger(__name__)

# Structured logging
logger.info("Starting diff operation", extra={
    "source_db": "production",
    "target_db": "staging",
    "schema_count": 5
})
```

## Implementation Status

All features described in this document are **not implemented** and represent planned future enhancements to pgdelta. The timeline for implementation depends on community feedback and development priorities.

**Priority Areas for Future Development:**
1. **Direct Database Connection Interface**: Connect to two databases and diff their catalogs
2. **Enhanced Python API**: Async support, streaming, schema filtering
3. **Configuration API**: YAML-based configuration for common workflows
4. **HTTP API**: REST API for web-based integrations
5. **Plugin System**: Extensible architecture for custom entity types
6. **Advanced Features**: Schema versioning, rollback generation, migration simulation

## Contributing

These planned features are subject to change based on community feedback and requirements.

To contribute to the planning process:
1. Review the [Contributing Guide](../contributing/setup.md)
2. Submit feature requests via GitHub Issues
3. Participate in design discussions
4. Help implement planned features

The roadmap prioritizes features based on:
- Community demand
- Technical feasibility
- Architectural consistency
- Performance impact
