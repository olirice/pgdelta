"""Unit tests for base model functionality."""

from dataclasses import dataclass, field

import pytest

from pgdelta.model.base import BasePgModel


def test_field_metadata():
    """Test field metadata for dataclass fields."""
    identity_field = field(metadata={"field_type": "identity"})
    data_field = field(metadata={"field_type": "data"})
    internal_field = field(metadata={"field_type": "internal"})

    assert identity_field.metadata == {"field_type": "identity"}
    assert data_field.metadata == {"field_type": "data"}
    assert internal_field.metadata == {"field_type": "internal"}


def test_semantic_equality_different_types():
    """Test semantic equality with different types."""

    @dataclass(slots=True, frozen=True)
    class ModelA(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})

        @property
        def stable_id(self) -> str:
            return self.name

    @dataclass(slots=True, frozen=True)
    class ModelB(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})

        @property
        def stable_id(self) -> str:
            return self.name

    a = ModelA(name="test", value=1)
    b = ModelB(name="test", value=1)

    # Different classes should not be equal
    assert not a.semantic_equality(b)


def test_semantic_equality_identity_mismatch():
    """Test semantic equality with identity field mismatch."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})
        internal_id: int = field(metadata={"field_type": "internal"})

        @property
        def stable_id(self) -> str:
            return self.name

    a = TestModel(name="test1", value=1, internal_id=100)
    b = TestModel(name="test2", value=1, internal_id=100)

    # Different identity fields should not be equal
    assert not a.semantic_equality(b)


def test_semantic_equality_data_mismatch():
    """Test semantic equality with data field mismatch."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})
        internal_id: int = field(metadata={"field_type": "internal"})

        @property
        def stable_id(self) -> str:
            return self.name

    a = TestModel(name="test", value=1, internal_id=100)
    b = TestModel(name="test", value=2, internal_id=100)

    # Different data fields should not be equal
    assert not a.semantic_equality(b)


def test_semantic_equality_internal_ignored():
    """Test semantic equality ignores internal fields."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})
        internal_id: int = field(metadata={"field_type": "internal"})

        @property
        def stable_id(self) -> str:
            return self.name

    a = TestModel(name="test", value=1, internal_id=100)
    b = TestModel(name="test", value=1, internal_id=200)

    # Different internal fields should still be equal
    assert a.semantic_equality(b)


def test_semantic_equality_same_object():
    """Test semantic equality with identical objects."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})
        internal_id: int = field(metadata={"field_type": "internal"})

        @property
        def stable_id(self) -> str:
            return self.name

    a = TestModel(name="test", value=1, internal_id=100)
    b = TestModel(name="test", value=1, internal_id=100)

    # Identical objects should be equal
    assert a.semantic_equality(b)


def test_get_identity_fields():
    """Test getting identity fields."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        description: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})
        internal_id: int = field(metadata={"field_type": "internal"})

        @property
        def stable_id(self) -> str:
            return self.name

    model = TestModel(name="test", description="desc", value=1, internal_id=100)
    identity_fields = model.get_identity_fields()

    assert identity_fields == {"name": "test", "description": "desc"}


def test_get_data_fields():
    """Test getting data fields."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})
        value: int = field(metadata={"field_type": "data"})
        config: str = field(metadata={"field_type": "data"})
        internal_id: int = field(metadata={"field_type": "internal"})

        @property
        def stable_id(self) -> str:
            return self.name

    model = TestModel(name="test", value=1, config="cfg", internal_id=100)
    data_fields = model.get_data_fields()

    assert data_fields == {"value": 1, "config": "cfg"}


def test_stable_id_abstract():
    """Test stable_id is abstract and must be implemented."""

    # Cannot instantiate BasePgModel directly due to abstract methods
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BasePgModel()


def test_model_config():
    """Test model configuration."""

    @dataclass(slots=True, frozen=True)
    class TestModel(BasePgModel):
        name: str = field(metadata={"field_type": "identity"})

        @property
        def stable_id(self) -> str:
            return self.name

    # Test model is frozen (immutable)
    model = TestModel(name="test")
    with pytest.raises(AttributeError):
        model.name = "new name"  # type: ignore

    # Test basic creation
    model2 = TestModel(name="test")
    assert model2.name == "test"
