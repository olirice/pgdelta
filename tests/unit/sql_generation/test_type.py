"""Type SQL generation tests."""

import pytest

from pgdelta.changes.dispatcher import generate_sql
from pgdelta.changes.type import (
    AlterTypeAddAttribute,
    AlterTypeAddValue,
    AlterTypeAlterAttribute,
    AlterTypeDropAttribute,
    AlterTypeOwnerTo,
    AlterTypeRename,
    AlterTypeRenameValue,
    AlterTypeSetSchema,
    CreateType,
    DropType,
)
from pgdelta.model.pg_type import CompositeAttribute


def test_create_enum_type_basic():
    """Test basic CREATE TYPE AS ENUM SQL generation."""
    change = CreateType(
        stable_id="type:public.mood",
        namespace="public",
        typname="mood",
        typtype="e",
        enum_values=["sad", "ok", "happy"],
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."mood"' in sql
    assert "AS ENUM ('sad', 'ok', 'happy')" in sql
    assert sql.endswith(";")


def test_create_enum_type_single_value():
    """Test CREATE TYPE AS ENUM with single value."""
    change = CreateType(
        stable_id="type:public.status",
        namespace="public",
        typname="status",
        typtype="e",
        enum_values=["active"],
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."status"' in sql
    assert "AS ENUM ('active')" in sql
    assert sql.endswith(";")


def test_create_enum_type_special_characters():
    """Test CREATE TYPE AS ENUM with special characters in schema and type names."""
    change = CreateType(
        stable_id="type:test-schema.user-status",
        namespace="test-schema",
        typname="user-status",
        typtype="e",
        enum_values=["pending", "approved", "rejected"],
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "test-schema"."user-status"' in sql
    assert "AS ENUM ('pending', 'approved', 'rejected')" in sql
    assert sql.endswith(";")


def test_create_domain_type_basic():
    """Test basic CREATE DOMAIN SQL generation."""
    change = CreateType(
        stable_id="type:public.positive_int",
        namespace="public",
        typname="positive_int",
        typtype="d",
        domain_base_type="INTEGER",
        domain_constraints=["CHECK ((VALUE > 0))"],
    )

    sql = generate_sql(change)

    assert 'CREATE DOMAIN "public"."positive_int"' in sql
    assert "AS INTEGER" in sql
    assert "CHECK ((VALUE > 0))" in sql
    assert sql.endswith(";")


def test_create_domain_type_multiple_constraints():
    """Test CREATE DOMAIN with multiple constraints."""
    change = CreateType(
        stable_id="type:public.valid_email",
        namespace="public",
        typname="valid_email",
        typtype="d",
        domain_base_type="TEXT",
        domain_constraints=[
            "CHECK ((VALUE ~ '^[^@]+@[^@]+\\.[^@]+$'::text))",
            "CHECK ((LENGTH(VALUE) <= 255))",
        ],
    )

    sql = generate_sql(change)

    assert 'CREATE DOMAIN "public"."valid_email"' in sql
    assert "AS TEXT" in sql
    assert "CHECK ((VALUE ~ '^[^@]+@[^@]+\\.[^@]+$'::text))" in sql
    assert "CHECK ((LENGTH(VALUE) <= 255))" in sql
    assert sql.endswith(";")


def test_create_composite_type_basic():
    """Test basic CREATE TYPE AS composite SQL generation."""
    change = CreateType(
        stable_id="type:public.address",
        namespace="public",
        typname="address",
        typtype="c",
        composite_attributes=[
            CompositeAttribute(
                name="street", type_name="VARCHAR(90)", position=1, not_null=False
            ),
            CompositeAttribute(
                name="city", type_name="VARCHAR(90)", position=2, not_null=False
            ),
            CompositeAttribute(
                name="state", type_name="VARCHAR(2)", position=3, not_null=True
            ),
        ],
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."address"' in sql
    assert '"street" VARCHAR(90)' in sql
    assert '"city" VARCHAR(90)' in sql
    assert '"state" VARCHAR(2) NOT NULL' in sql
    assert sql.endswith(");")


def test_create_range_type_basic():
    """Test basic CREATE TYPE AS RANGE SQL generation."""
    change = CreateType(
        stable_id="type:public.floatrange",
        namespace="public",
        typname="floatrange",
        typtype="r",
        range_subtype="float8",
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."floatrange"' in sql
    assert "AS RANGE (subtype = float8)" in sql
    assert sql.endswith(";")


def test_drop_type_basic():
    """Test basic DROP TYPE SQL generation."""
    change = DropType(
        stable_id="type:public.old_enum",
        namespace="public",
        typname="old_enum",
    )

    sql = generate_sql(change)

    assert sql == 'DROP TYPE "public"."old_enum";'


def test_drop_type_special_characters():
    """Test DROP TYPE with special characters in names."""
    change = DropType(
        stable_id="type:test-schema.old-type",
        namespace="test-schema",
        typname="old-type",
    )

    sql = generate_sql(change)

    assert sql == 'DROP TYPE "test-schema"."old-type";'


@pytest.mark.parametrize(
    "namespace,typname,expected_quoted",
    [
        ("public", "simple", '"public"."simple"'),
        ("test-schema", "type-name", '"test-schema"."type-name"'),
        (
            "schema_underscore",
            "type_underscore",
            '"schema_underscore"."type_underscore"',
        ),
        ("schema space", "type space", '"schema space"."type space"'),
        ("SCHEMA_CAPS", "TYPE_CAPS", '"SCHEMA_CAPS"."TYPE_CAPS"'),
    ],
)
def test_type_name_quoting(namespace, typname, expected_quoted):
    """Test that schema and type names are properly quoted."""
    create_change = CreateType(
        stable_id=f"type:{namespace}.{typname}",
        namespace=namespace,
        typname=typname,
        typtype="e",
        enum_values=["value1"],
    )

    create_sql = generate_sql(create_change)
    assert expected_quoted in create_sql

    drop_change = DropType(
        stable_id=f"type:{namespace}.{typname}",
        namespace=namespace,
        typname=typname,
    )

    drop_sql = generate_sql(drop_change)
    assert expected_quoted in drop_sql


def test_create_enum_type_error_no_values():
    """Test that CREATE TYPE AS ENUM fails without enum values."""
    change = CreateType(
        stable_id="type:public.bad_enum",
        namespace="public",
        typname="bad_enum",
        typtype="e",
        enum_values=None,
    )

    with pytest.raises(ValueError, match="Enum type .* must have enum_values"):
        generate_sql(change)


def test_create_domain_type_error_no_base_type():
    """Test that CREATE DOMAIN fails without base type."""
    change = CreateType(
        stable_id="type:public.bad_domain",
        namespace="public",
        typname="bad_domain",
        typtype="d",
        domain_base_type=None,
    )

    with pytest.raises(ValueError, match="Domain type .* must have domain_base_type"):
        generate_sql(change)


def test_create_composite_type_error_no_attributes():
    """Test that CREATE TYPE AS composite fails without attributes."""
    change = CreateType(
        stable_id="type:public.bad_composite",
        namespace="public",
        typname="bad_composite",
        typtype="c",
        composite_attributes=None,
    )

    with pytest.raises(
        ValueError, match="Composite type .* must have composite_attributes"
    ):
        generate_sql(change)


def test_create_range_type_error_no_subtype():
    """Test that CREATE TYPE AS RANGE fails without subtype."""
    change = CreateType(
        stable_id="type:public.bad_range",
        namespace="public",
        typname="bad_range",
        typtype="r",
        range_subtype=None,
    )

    with pytest.raises(ValueError, match="Range type .* must have range_subtype"):
        generate_sql(change)


def test_create_type_unsupported_category():
    """Test that unsupported type categories raise an error."""
    change = CreateType(
        stable_id="type:public.bad_type",
        namespace="public",
        typname="bad_type",
        typtype="x",  # Unsupported type category
    )

    with pytest.raises(ValueError, match="Unsupported type category: x"):
        generate_sql(change)


# Base Type Tests


def test_create_base_type_basic():
    """Test basic CREATE TYPE (base type) SQL generation."""
    change = CreateType(
        stable_id="type:public.complex",
        namespace="public",
        typname="complex",
        typtype="b",
        base_input_function="complex_in",
        base_output_function="complex_out",
        base_internallength=16,
        base_passedbyvalue=False,
        base_alignment="double",
        base_storage="plain",
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."complex"' in sql
    assert "INPUT = complex_in" in sql
    assert "OUTPUT = complex_out" in sql
    assert "INTERNALLENGTH = 16" in sql
    assert "PASSEDBYVALUE = FALSE" in sql
    assert "ALIGNMENT = double" in sql
    assert "STORAGE = plain" in sql
    assert sql.endswith(");")


def test_create_base_type_variable_length():
    """Test CREATE TYPE (base type) with variable length."""
    change = CreateType(
        stable_id="type:public.vartype",
        namespace="public",
        typname="vartype",
        typtype="b",
        base_input_function="vartype_in",
        base_output_function="vartype_out",
        base_internallength=-1,  # VARIABLE
    )

    sql = generate_sql(change)

    assert "INTERNALLENGTH = VARIABLE" in sql


def test_create_base_type_all_options():
    """Test CREATE TYPE (base type) with all possible options."""
    change = CreateType(
        stable_id="type:public.fulltype",
        namespace="public",
        typname="fulltype",
        typtype="b",
        base_input_function="fulltype_in",
        base_output_function="fulltype_out",
        base_receive_function="fulltype_recv",
        base_send_function="fulltype_send",
        base_typmod_in_function="fulltype_typmod_in",
        base_typmod_out_function="fulltype_typmod_out",
        base_analyze_function="fulltype_analyze",
        base_internallength=8,
        base_passedbyvalue=True,
        base_alignment="int4",
        base_storage="extended",
        base_like_type="int4",
        base_category="N",
        base_preferred=True,
        base_default="0",
        base_element="int4",
        base_delimiter=",",
        base_collatable=False,
    )

    sql = generate_sql(change)

    expected_parts = [
        "INPUT = fulltype_in",
        "OUTPUT = fulltype_out",
        "RECEIVE = fulltype_recv",
        "SEND = fulltype_send",
        "TYPMOD_IN = fulltype_typmod_in",
        "TYPMOD_OUT = fulltype_typmod_out",
        "ANALYZE = fulltype_analyze",
        "INTERNALLENGTH = 8",
        "PASSEDBYVALUE = TRUE",
        "ALIGNMENT = int4",
        "STORAGE = extended",
        "LIKE = int4",
        "CATEGORY = 'N'",
        "PREFERRED = TRUE",
        "DEFAULT = '0'",
        "ELEMENT = int4",
        "DELIMITER = ','",
        "COLLATABLE = FALSE",
    ]

    for part in expected_parts:
        assert part in sql


def test_create_multirange_type():
    """Test CREATE TYPE AS MULTIRANGE SQL generation."""
    change = CreateType(
        stable_id="type:public.int4multirange",
        namespace="public",
        typname="int4multirange",
        typtype="m",
        multirange_range_type="int4range",
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."int4multirange"' in sql
    assert "AS MULTIRANGE (range_type = int4range)" in sql
    assert sql.endswith(";")


def test_create_range_type_extended():
    """Test CREATE TYPE AS RANGE with extended options."""
    change = CreateType(
        stable_id="type:public.customrange",
        namespace="public",
        typname="customrange",
        typtype="r",
        range_subtype="int4",
        range_subtype_diff="int4_diff",
        range_canonical="int4_canonical",
        range_subtype_opclass="int4_ops",
        range_collation="C",
    )

    sql = generate_sql(change)

    assert 'CREATE TYPE "public"."customrange"' in sql
    assert "AS RANGE (" in sql
    assert "subtype = int4" in sql
    assert "subtype_diff = int4_diff" in sql
    assert "canonical = int4_canonical" in sql
    assert "subtype_opclass = int4_ops" in sql
    assert "collation = C" in sql
    assert sql.endswith(");")


# ALTER TYPE Tests


def test_alter_type_owner_to():
    """Test ALTER TYPE ... OWNER TO SQL generation."""
    change = AlterTypeOwnerTo(
        stable_id="type:public.mood",
        namespace="public",
        typname="mood",
        new_owner="new_user",
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TYPE "public"."mood" OWNER TO new_user;'


def test_alter_type_rename():
    """Test ALTER TYPE ... RENAME TO SQL generation."""
    change = AlterTypeRename(
        stable_id="type:public.old_name",
        namespace="public",
        typname="old_name",
        new_name="new_name",
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TYPE "public"."old_name" RENAME TO "new_name";'


def test_alter_type_set_schema():
    """Test ALTER TYPE ... SET SCHEMA SQL generation."""
    change = AlterTypeSetSchema(
        stable_id="type:old_schema.mood",
        namespace="old_schema",
        typname="mood",
        new_schema="new_schema",
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TYPE "old_schema"."mood" SET SCHEMA "new_schema";'


def test_alter_type_add_attribute():
    """Test ALTER TYPE ... ADD ATTRIBUTE SQL generation."""
    change = AlterTypeAddAttribute(
        stable_id="type:public.address",
        namespace="public",
        typname="address",
        attribute_name="zip_code",
        attribute_type="VARCHAR(10)",
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TYPE "public"."address" ADD ATTRIBUTE "zip_code" VARCHAR(10);'


def test_alter_type_drop_attribute():
    """Test ALTER TYPE ... DROP ATTRIBUTE SQL generation."""
    change = AlterTypeDropAttribute(
        stable_id="type:public.address",
        namespace="public",
        typname="address",
        attribute_name="old_field",
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TYPE "public"."address" DROP ATTRIBUTE "old_field";'


def test_alter_type_alter_attribute():
    """Test ALTER TYPE ... ALTER ATTRIBUTE ... TYPE SQL generation."""
    change = AlterTypeAlterAttribute(
        stable_id="type:public.address",
        namespace="public",
        typname="address",
        attribute_name="zip_code",
        new_type="VARCHAR(20)",
    )

    sql = generate_sql(change)

    assert (
        sql
        == 'ALTER TYPE "public"."address" ALTER ATTRIBUTE "zip_code" TYPE VARCHAR(20);'
    )


def test_alter_type_add_value():
    """Test ALTER TYPE ... ADD VALUE SQL generation."""
    change = AlterTypeAddValue(
        stable_id="type:public.mood",
        namespace="public",
        typname="mood",
        new_value="excited",
    )

    sql = generate_sql(change)

    assert sql == 'ALTER TYPE "public"."mood" ADD VALUE \'excited\';'


def test_alter_type_add_value_before():
    """Test ALTER TYPE ... ADD VALUE BEFORE SQL generation."""
    change = AlterTypeAddValue(
        stable_id="type:public.mood",
        namespace="public",
        typname="mood",
        new_value="excited",
        before_value="happy",
    )

    sql = generate_sql(change)

    assert sql == "ALTER TYPE \"public\".\"mood\" ADD VALUE 'excited' BEFORE 'happy';"


def test_alter_type_add_value_after():
    """Test ALTER TYPE ... ADD VALUE AFTER SQL generation."""
    change = AlterTypeAddValue(
        stable_id="type:public.mood",
        namespace="public",
        typname="mood",
        new_value="excited",
        after_value="happy",
    )

    sql = generate_sql(change)

    assert sql == "ALTER TYPE \"public\".\"mood\" ADD VALUE 'excited' AFTER 'happy';"


def test_alter_type_rename_value():
    """Test ALTER TYPE ... RENAME VALUE SQL generation."""
    change = AlterTypeRenameValue(
        stable_id="type:public.mood",
        namespace="public",
        typname="mood",
        old_value="ok",
        new_value="neutral",
    )

    sql = generate_sql(change)

    assert sql == "ALTER TYPE \"public\".\"mood\" RENAME VALUE 'ok' TO 'neutral';"


# Error Tests for Base Types


def test_create_base_type_error_no_input_function():
    """Test that CREATE TYPE (base type) fails without input function."""
    change = CreateType(
        stable_id="type:public.bad_base",
        namespace="public",
        typname="bad_base",
        typtype="b",
        base_input_function=None,
        base_output_function="bad_base_out",
    )

    with pytest.raises(
        ValueError, match="Base type .* must have input and output functions"
    ):
        generate_sql(change)


def test_create_base_type_error_no_output_function():
    """Test that CREATE TYPE (base type) fails without output function."""
    change = CreateType(
        stable_id="type:public.bad_base",
        namespace="public",
        typname="bad_base",
        typtype="b",
        base_input_function="bad_base_in",
        base_output_function=None,
    )

    with pytest.raises(
        ValueError, match="Base type .* must have input and output functions"
    ):
        generate_sql(change)


def test_create_multirange_type_error_no_range_type():
    """Test that CREATE TYPE AS MULTIRANGE fails without range type."""
    change = CreateType(
        stable_id="type:public.bad_multirange",
        namespace="public",
        typname="bad_multirange",
        typtype="m",
        multirange_range_type=None,
    )

    with pytest.raises(
        ValueError, match="Multirange type .* must have multirange_range_type"
    ):
        generate_sql(change)


# Test special characters in ALTER TYPE operations


def test_alter_type_special_characters():
    """Test ALTER TYPE operations with special characters in names."""
    # Test with schema and type names containing special characters
    namespace = "test-schema"
    typname = "test-type"

    owner_change = AlterTypeOwnerTo(
        stable_id=f"type:{namespace}.{typname}",
        namespace=namespace,
        typname=typname,
        new_owner="test-user",
    )

    sql = generate_sql(owner_change)
    assert f'ALTER TYPE "{namespace}"."{typname}" OWNER TO test-user;' == sql

    rename_change = AlterTypeRename(
        stable_id=f"type:{namespace}.{typname}",
        namespace=namespace,
        typname=typname,
        new_name="new-name",
    )

    sql = generate_sql(rename_change)
    assert f'ALTER TYPE "{namespace}"."{typname}" RENAME TO "new-name";' == sql
