"""Tests for serialization helpers."""

import json

import pytest

from tkseal.serializers import (
    get_serializer,
    YAMLSerializer,
)


@pytest.fixture
def sample_secrets_with_multiline():
    """Sample secrets with multiline values (e.g., config files)."""
    return [
        {
            "name": "config-secret",
            "data": {
                "config.yml": "database:\n  host: localhost\n  port: 5432\n",
                "single_line": "simple_value",
            },
            "type": "Opaque",
        }
    ]


@pytest.mark.parametrize("format", ["json", "yaml"])
def test_serialize_deserialize_roundtrip(sample_plain_secrets_multiple, format):
    """Test round-trip serialization and deserialization for both formats."""

    sample_secrets_data_multiple: list[dict] = json.loads(sample_plain_secrets_multiple)

    secret_serializer = get_serializer(format)

    # Serialize to string
    serialized = secret_serializer.serialize_secrets(sample_secrets_data_multiple)

    # Verify it's a string
    assert isinstance(serialized, str)
    assert len(serialized) > 0



    # Deserialize back to Python objects
    deserialized = secret_serializer.deserialize_secrets(serialized)

    # Verify the structure is preserved
    assert deserialized == sample_secrets_data_multiple
    assert len(deserialized) == 2
    assert deserialized[0]["name"] == "app-secret"
    assert deserialized[0]["data"]["username"] == "admin"
    assert deserialized[1]["name"] == "db-secret"


def test_yaml_preserves_multiline_formatting(sample_secrets_with_multiline):
    """Test that YAML format preserves multiline strings with block scalar style."""

    format = "yaml"
    secret_serializer = get_serializer("yaml")

    assert isinstance(secret_serializer, YAMLSerializer)

    # Serialize to YAML
    yaml_output = secret_serializer.serialize_secrets(sample_secrets_with_multiline)

    # Verify multiline string uses block scalar style (|)
    assert "|" in yaml_output or "|-" in yaml_output
    # Verify the multiline content is preserved
    assert "database:" in yaml_output
    assert "host: localhost" in yaml_output
    assert "port: 5432" in yaml_output

    # Verify single-line values work normally
    assert "simple_value" in yaml_output



    # Verify round-trip preserves content
    deserialized = secret_serializer.deserialize_secrets(yaml_output)
    assert (
        deserialized[0]["data"]["config.yml"]
        == sample_secrets_with_multiline[0]["data"]["config.yml"]
    )
    assert deserialized[0]["data"]["single_line"] == "simple_value"


def test_invalid_format_raises_error(sample_plain_secrets):
    """Test that invalid format raises ValueError."""

    # Test serialize with invalid format
    with pytest.raises(ValueError, match="Unsupported format"):
        secret_serializer = get_serializer("xml")
        #serialize_secrets(json.loads(sample_plain_secrets), format="xml")

    # Test deserialize with invalid format
    #with pytest.raises(ValueError, match="Unsupported format"):
    #    deserialize_secrets('{"test": "data"}', format="xml")