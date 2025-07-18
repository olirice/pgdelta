"""Type extraction tests."""

from unittest.mock import Mock

from pgdelta.model.pg_type import (
    CompositeAttribute,
    _extract_composite_attributes,
    _extract_domain_info,
    _extract_enum_values,
    _extract_range_subtype,
    extract_types,
)


class TestTypeExtraction:
    """Test type extraction functions."""

    def test_extract_types_empty_namespaces(self):
        """Test extraction with empty namespace list."""
        session = Mock()

        types = extract_types(session, [])

        assert types == []
        session.execute.assert_not_called()

    def test_extract_types_basic_enum(self):
        """Test extracting a basic enum type."""
        session = Mock()

        # Mock the main query result
        main_result = Mock()
        main_result.__iter__ = Mock(
            return_value=iter(
                [
                    Mock(
                        oid=1234,
                        typname="mood",
                        namespace="public",
                        typtype="e",
                        typlen=-1,
                        typbyval=False,
                        typcategory="U",
                        typisdefined=True,
                        typdelim=",",
                        typelem=None,
                        typarray=None,
                        typrelid=None,
                        typinput=100,
                        typoutput=101,
                        typreceive=102,
                        typsend=103,
                    )
                ]
            )
        )

        # Mock enum values query
        enum_result = Mock()
        enum_result.__iter__ = Mock(
            return_value=iter(
                [
                    Mock(enumlabel="sad"),
                    Mock(enumlabel="happy"),
                ]
            )
        )

        # Set up session.execute to return different results for different queries
        def side_effect(query, params):
            if "pg_enum" in str(query):
                return enum_result
            else:
                return main_result

        session.execute.side_effect = side_effect

        types = extract_types(session, [123])

        assert len(types) == 1

        pg_type = types[0]
        assert pg_type.typname == "mood"
        assert pg_type.namespace == "public"
        assert pg_type.typtype == "e"
        assert pg_type.enum_values == ["sad", "happy"]
        assert pg_type.domain_base_type is None
        assert pg_type.domain_constraints is None
        assert pg_type.composite_attributes is None
        assert pg_type.range_subtype is None

    def test_extract_enum_values(self):
        """Test extracting enum values."""
        session = Mock()
        result = Mock()
        result.__iter__ = Mock(
            return_value=iter(
                [
                    Mock(enumlabel="pending"),
                    Mock(enumlabel="approved"),
                    Mock(enumlabel="rejected"),
                ]
            )
        )
        session.execute.return_value = result

        values = _extract_enum_values(session, 1234)

        assert values == ["pending", "approved", "rejected"]
        session.execute.assert_called_once()

    def test_extract_domain_info_with_constraint(self):
        """Test extracting domain base type and constraints."""
        session = Mock()

        # Mock base type query
        base_result = Mock()
        base_result.fetchone.return_value = Mock(base_type="INTEGER")

        # Mock constraints query
        constraints_result = Mock()
        constraints_result.__iter__ = Mock(
            return_value=iter(
                [
                    Mock(constraint_def="CHECK ((VALUE > 0))"),
                    Mock(constraint_def="CHECK ((VALUE <= 100))"),
                ]
            )
        )

        def side_effect(query, params):
            if "format_type" in str(query):
                return base_result
            else:
                return constraints_result

        session.execute.side_effect = side_effect

        base_type, constraints = _extract_domain_info(session, 1234)

        assert base_type == "INTEGER"
        assert constraints == ["CHECK ((VALUE > 0))", "CHECK ((VALUE <= 100))"]

    def test_extract_domain_info_no_constraints(self):
        """Test extracting domain with no constraints."""
        session = Mock()

        base_result = Mock()
        base_result.fetchone.return_value = Mock(base_type="TEXT")

        constraints_result = Mock()
        constraints_result.__iter__ = Mock(return_value=iter([]))

        def side_effect(query, params):
            if "format_type" in str(query):
                return base_result
            else:
                return constraints_result

        session.execute.side_effect = side_effect

        base_type, constraints = _extract_domain_info(session, 1234)

        assert base_type == "TEXT"
        assert constraints is None

    def test_extract_composite_attributes(self):
        """Test extracting composite type attributes."""
        session = Mock()
        result = Mock()
        result.__iter__ = Mock(
            return_value=iter(
                [
                    Mock(
                        attname="street",
                        atttype="VARCHAR(90)",
                        attnum=1,
                        attnotnull=False,
                    ),
                    Mock(
                        attname="city",
                        atttype="VARCHAR(90)",
                        attnum=2,
                        attnotnull=False,
                    ),
                    Mock(
                        attname="zip_code",
                        atttype="VARCHAR(10)",
                        attnum=3,
                        attnotnull=True,
                    ),
                ]
            )
        )
        session.execute.return_value = result

        attributes = _extract_composite_attributes(session, 1234)

        assert len(attributes) == 3
        assert attributes[0] == CompositeAttribute(
            name="street",
            type_name="VARCHAR(90)",
            position=1,
            not_null=False,
        )
        assert attributes[2].not_null is True

    def test_extract_composite_attributes_empty(self):
        """Test extracting composite type with no attributes."""
        session = Mock()
        result = Mock()
        result.__iter__ = Mock(return_value=iter([]))
        session.execute.return_value = result

        attributes = _extract_composite_attributes(session, 1234)

        assert attributes is None

    def test_extract_range_subtype(self):
        """Test extracting range subtype."""
        session = Mock()
        result = Mock()
        result.fetchone.return_value = Mock(subtype="float8")
        session.execute.return_value = result

        subtype = _extract_range_subtype(session, 1234)

        assert subtype == "float8"

    def test_extract_range_subtype_not_found(self):
        """Test extracting range subtype when not found."""
        session = Mock()
        result = Mock()
        result.fetchone.return_value = None
        session.execute.return_value = result

        subtype = _extract_range_subtype(session, 1234)

        assert subtype is None
