"""Serialization helpers for converting secrets between JSON and YAML formats."""

import json
from abc import ABC

import yaml


def _str_presenter(dumper, data):
    """
    Custom YAML representer for strings that preserves multiline formatting.

    Uses block scalar style (|) for strings containing newlines,
    ensuring readable YAML output for config files, certificates, etc.
    Implementation inspired by: https://www.hrekov.com/blog/yaml-formatting-custom-representer
    """
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Register custom representer for multiline string preservation
yaml.add_representer(str, _str_presenter)

class Serializer(ABC):
    """Abstract base class for serializer secrets."""

    def serialize_secrets(self, data: list[dict]) -> str:
        """Serialize secret data to a string."""
        pass

    def deserialize_secrets(self, content: str) -> list[dict]:
        """Deserialize secret data from a string."""
        pass

class YAMLSerializer(Serializer):
    """YAML serializer for secrets."""

    def serialize_secrets(self, data: list[dict]) -> str:
        """
        Serialize secret data to YAML format.

        Args:
            data: List of secret dictionaries to serialize
            format: Output format 'yaml'

        Returns:
            Serialized string in the YAML format
        """
        return yaml.dump(
            data,
            default_flow_style=False, # Controls the output style.
            # False means indented block format.
            # with each item
            # on a new line.
            # Preferred output for config files.
            sort_keys=False,
            allow_unicode=True,
        )

    def deserialize_secrets(self, content: str) -> list[dict]:
        """
        Deserialize secret data from YAML format.

        Args:
            content: Serialized string to deserialize
            format: Input format 'yaml'

        Returns:
            List of secret dictionaries
        """
        return yaml.safe_load(content)

class JSONSerializer(Serializer):
    """JSON serializer for secrets."""

    def serialize_secrets(self, data: list[dict]) -> str:
        """
        Serialize secret data to JSON.

        Args:
            data: List of secret dictionaries to serialize
            format: Output format 'json'

        Returns:
            Serialized string in the JSON format
        """
        return json.dumps(data, indent=2)

    def deserialize_secrets(self, content: str) -> list[dict]:

        """
        Deserialize secret data from JSON format.

        Args:
            content: Serialized string to deserialize
            format: Input format 'json'

        Returns:
            List of secret dictionaries

        """

        return json.loads(content)

def get_serializer(format: str) -> Serializer:
    """
    Factory function to get the appropriate serializer based on format.

    Args:
        format: 'json' or 'yaml'

    Returns:
        Serializer instance

    Raises:
        ValueError: If the format is not 'json' or 'yaml'
    """
    if format == "json":
        return JSONSerializer()
    elif format == "yaml":
        return YAMLSerializer()
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'yaml'.")

