# Supported Entities Overview

This page provides a comprehensive overview of PostgreSQL entities supported by pgdelta, organized by operation type.

## Support Status Legend

- ✅ **Supported**: Full implementation with comprehensive test coverage
- ❌ **Not Supported**: Not yet implemented, may be planned for future release
- 🚫 **Not Applicable**: Operation doesn't apply to this entity type
- 🔄 **Partial**: Limited implementation, see entity details below

## Entity Support Matrix

| Entity | CREATE | DROP | ALTER | REPLACE | Notes |
|--------|--------|------|-------|---------|-------|
| [Schemas](#schemas) | ✅ | ✅ | ❌ | 🚫 | Basic schema lifecycle |
| [Tables](#tables) | ✅ | ✅ | ✅ | 🚫 | Full table support with columns |
| [Constraints](#constraints) | ✅ | ✅ | 🔄 | 🚫 | All constraint types |
| [Indexes](#indexes) | ✅ | ✅ | ❌ | 🚫 | All index types and methods |
| [Views](#views) | ✅ | ✅ | ❌ | ✅ | Basic view support |
| [Materialized Views](#materialized-views) | ✅ | ✅ | ❌ | ✅ | Created with NO DATA |
| [Functions](#functions) | ✅ | ✅ | ❌ | ✅ | All function types via pg_get_functiondef |
| [Triggers](#triggers) | ✅ | ✅ | ❌ | ❌ | All trigger types via pg_get_triggerdef |
| [Sequences](#sequences) | ✅ | ✅ | ✅ | 🚫 | Sequence support with OWNED BY |
| [Types](#types) | ✅ | ✅ | ✅ | 🚫 | Enum, composite, and domain types |
| [Policies](#policies) | ✅ | ✅ | ✅ | 🚫 | Row Level Security policies |
| Comments | ❌ | ❌ | ❌ | 🚫 |  |
| Roles | ❌ | ❌ | ❌ | 🚫 |  |
| Grants | ❌ | ❌ | 🚫 | 🚫 | |
| Default Privileges | 🚫 | 🚫 | ❌ | 🚫 |  |

## Contributing

To contribute support for new entity features:
1. Review the [Contributing Guide](../contributing/setup.md)
2. Follow the [Adding New Entities](../contributing/adding-entities.md) guide
3. Ensure comprehensive test coverage with real PostgreSQL
4. Maintain roundtrip fidelity

The project prioritizes correctness and completeness over speed of implementation.
