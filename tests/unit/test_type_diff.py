"""Type diff logic tests."""

from pgdelta.catalog import catalog
from pgdelta.changes.type import CreateType, DropType
from pgdelta.diff.pg_type_diff import diff_types
from pgdelta.model.pg_type import PgType


def create_test_type(
    typname: str,
    namespace: str = "public",
    typtype: str = "e",
    oid: int = 1234,
    **kwargs,
) -> PgType:
    """Helper to create a test PgType."""
    return PgType(
        oid=oid,
        typname=typname,
        namespace=namespace,
        typtype=typtype,
        typlen=-1,
        typbyval=False,
        typcategory="U",
        typisdefined=True,
        typdelim=",",
        typinput=0,
        typoutput=0,
        typreceive=0,
        typsend=0,
        **kwargs,
    )


def create_test_catalog(*types: PgType):
    """Helper to create a test catalog with only types populated."""
    return catalog(types=list(types))


def test_diff_types_no_changes():
    """Test that identical type catalogs produce no changes."""
    enum_type = create_test_type("mood", enum_values=["sad", "happy"])

    master_catalog = create_test_catalog(enum_type)
    branch_catalog = create_test_catalog(enum_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 0


def test_diff_types_create_enum():
    """Test creating a new enum type."""
    enum_type = create_test_type("mood", enum_values=["sad", "happy"])

    master_catalog = create_test_catalog()
    branch_catalog = create_test_catalog(enum_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 1

    change = changes[0]
    assert isinstance(change, CreateType)
    assert change.stable_id == "type:public.mood"
    assert change.typname == "mood"
    assert change.namespace == "public"
    assert change.typtype == "e"
    assert change.enum_values == ["sad", "happy"]


def test_diff_types_drop_enum():
    """Test dropping an enum type."""
    enum_type = create_test_type("mood", enum_values=["sad", "happy"])

    master_catalog = create_test_catalog(enum_type)
    branch_catalog = create_test_catalog()

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 1

    change = changes[0]
    assert isinstance(change, DropType)
    assert change.stable_id == "type:public.mood"
    assert change.typname == "mood"
    assert change.namespace == "public"


def test_diff_types_create_domain():
    """Test creating a domain type."""
    domain_type = create_test_type(
        "positive_int",
        typtype="d",
        domain_base_type="INTEGER",
        domain_constraints=["VALUE > 0"],
    )

    master_catalog = create_test_catalog()
    branch_catalog = create_test_catalog(domain_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 1

    change = changes[0]
    assert isinstance(change, CreateType)
    assert change.stable_id == "type:public.positive_int"
    assert change.typtype == "d"
    assert change.domain_base_type == "INTEGER"
    assert change.domain_constraints == ["VALUE > 0"]


def test_diff_types_create_composite():
    """Test creating a composite type."""
    composite_type = create_test_type(
        "address",
        typtype="c",
        composite_attributes=[
            {"name": "street", "type": "TEXT", "position": 1, "not_null": False},
            {"name": "city", "type": "TEXT", "position": 2, "not_null": False},
        ],
    )

    master_catalog = create_test_catalog()
    branch_catalog = create_test_catalog(composite_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 1

    change = changes[0]
    assert isinstance(change, CreateType)
    assert change.stable_id == "type:public.address"
    assert change.typtype == "c"
    assert len(change.composite_attributes) == 2
    assert change.composite_attributes[0]["name"] == "street"


def test_diff_types_create_range():
    """Test creating a range type."""
    range_type = create_test_type(
        "floatrange",
        typtype="r",
        range_subtype="float8",
    )

    master_catalog = create_test_catalog()
    branch_catalog = create_test_catalog(range_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 1

    change = changes[0]
    assert isinstance(change, CreateType)
    assert change.stable_id == "type:public.floatrange"
    assert change.typtype == "r"
    assert change.range_subtype == "float8"


def test_diff_types_modify_enum_values():
    """Test modifying enum values results in DROP + CREATE."""
    master_type = create_test_type("mood", enum_values=["sad", "happy"])
    branch_type = create_test_type("mood", enum_values=["sad", "happy", "excited"])

    master_catalog = create_test_catalog(master_type)
    branch_catalog = create_test_catalog(branch_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 2

    # Should be DROP followed by CREATE
    drop_change = changes[0]
    create_change = changes[1]

    assert isinstance(drop_change, DropType)
    assert drop_change.stable_id == "type:public.mood"
    # No CASCADE support - rely on pg_depend for dependency resolution

    assert isinstance(create_change, CreateType)
    assert create_change.stable_id == "type:public.mood"
    assert create_change.enum_values == ["sad", "happy", "excited"]


def test_diff_types_modify_domain_constraint():
    """Test modifying domain constraints results in DROP + CREATE."""
    master_type = create_test_type(
        "positive_int",
        typtype="d",
        domain_base_type="INTEGER",
        domain_constraints=["VALUE > 0"],
    )
    branch_type = create_test_type(
        "positive_int",
        typtype="d",
        domain_base_type="INTEGER",
        domain_constraints=["VALUE >= 0", "VALUE <= 100"],
    )

    master_catalog = create_test_catalog(master_type)
    branch_catalog = create_test_catalog(branch_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 2

    drop_change = changes[0]
    create_change = changes[1]

    assert isinstance(drop_change, DropType)
    # No CASCADE support - rely on pg_depend for dependency resolution

    assert isinstance(create_change, CreateType)
    assert create_change.domain_constraints == ["VALUE >= 0", "VALUE <= 100"]


def test_diff_types_modify_composite_attributes():
    """Test modifying composite attributes results in DROP + CREATE."""
    master_type = create_test_type(
        "address",
        typtype="c",
        composite_attributes=[
            {"name": "street", "type": "TEXT", "position": 1, "not_null": False},
            {"name": "city", "type": "TEXT", "position": 2, "not_null": False},
        ],
    )
    branch_type = create_test_type(
        "address",
        typtype="c",
        composite_attributes=[
            {"name": "street", "type": "TEXT", "position": 1, "not_null": False},
            {"name": "city", "type": "TEXT", "position": 2, "not_null": False},
            {"name": "zip_code", "type": "TEXT", "position": 3, "not_null": False},
        ],
    )

    master_catalog = create_test_catalog(master_type)
    branch_catalog = create_test_catalog(branch_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 2

    drop_change = changes[0]
    create_change = changes[1]

    assert isinstance(drop_change, DropType)
    assert isinstance(create_change, CreateType)
    assert len(create_change.composite_attributes) == 3


def test_diff_types_multiple_operations():
    """Test multiple type operations in one diff."""
    # Create different types for master and branch
    master_enum = create_test_type("old_enum", enum_values=["a", "b"])
    master_domain = create_test_type(
        "old_domain",
        typtype="d",
        domain_base_type="INTEGER",
        domain_constraints=["VALUE > 0"],
    )

    branch_enum = create_test_type("new_enum", enum_values=["x", "y", "z"])
    branch_domain = create_test_type(
        "old_domain",
        typtype="d",
        domain_base_type="INTEGER",
        domain_constraints=["VALUE >= 0"],  # Modified constraint
    )

    master_catalog = create_test_catalog(master_enum, master_domain)
    branch_catalog = create_test_catalog(branch_enum, branch_domain)

    changes = diff_types(master_catalog, branch_catalog)

    # Should have: DROP old_enum, DROP old_domain, CREATE old_domain, CREATE new_enum
    assert len(changes) == 4

    # Check that we have the right mix of operations
    drops = [c for c in changes if isinstance(c, DropType)]
    creates = [c for c in changes if isinstance(c, CreateType)]

    assert len(drops) == 2
    assert len(creates) == 2

    # Check specific changes
    old_enum_drops = [c for c in drops if c.typname == "old_enum"]
    old_domain_drops = [c for c in drops if c.typname == "old_domain"]
    new_enum_creates = [c for c in creates if c.typname == "new_enum"]
    old_domain_creates = [c for c in creates if c.typname == "old_domain"]

    assert len(old_enum_drops) == 1
    assert len(old_domain_drops) == 1
    assert len(new_enum_creates) == 1
    assert len(old_domain_creates) == 1


def test_diff_types_different_namespaces():
    """Test types in different namespaces."""
    public_type = create_test_type("mood", namespace="public", enum_values=["a", "b"])
    test_type = create_test_type(
        "mood", namespace="test_schema", enum_values=["x", "y"]
    )

    master_catalog = create_test_catalog(public_type)
    branch_catalog = create_test_catalog(public_type, test_type)

    changes = diff_types(master_catalog, branch_catalog)
    assert len(changes) == 1

    change = changes[0]
    assert isinstance(change, CreateType)
    assert change.stable_id == "type:test_schema.mood"
    assert change.namespace == "test_schema"
