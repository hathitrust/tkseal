"""Serialization helpers for converting secrets between JSON and YAML formats."""

import json

import yaml


def _str_presenter(dumper, data):
    """
    Custom YAML representer for strings that preserves multiline formatting.

    Uses block scalar style (|) for strings containing newlines,
    ensuring readable YAML output for config files, certificates, etc.
    """
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Register custom representer for multiline string preservation
yaml.add_representer(str, _str_presenter)


def serialize_secrets(data: list[dict], format: str = "json") -> str:
    """
    Serialize secret data to JSON or YAML format.

    Args:
        data: List of secret dictionaries to serialize
        format: Output format ('json' or 'yaml')

    Returns:
        Serialized string in the specified format

    Raises:
        ValueError: If the format is not 'json' or 'yaml'
    """
    if format == "json":
        return json.dumps(data, indent=2)
    elif format == "yaml":
        return yaml.dump(
            data,
            default_flow_style=False, # Controls the output style. False means indented block forma. with each item on a new line. Preferred output for config files.
            sort_keys=False,
            allow_unicode=True,
        )
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'yaml'.")


def deserialize_secrets(content: str, format: str = "json") -> list[dict]:
    """
    Deserialize secret data from JSON or YAML format.

    Args:
        content: Serialized string to deserialize
        format: Input format ('json' or 'yaml')

    Returns:
        List of secret dictionaries

    Raises:
        ValueError: If the format is not 'json' or 'yaml'
    """
    if format == "json":
        return json.loads(content)
    elif format == "yaml":
        return yaml.safe_load(content)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'yaml'.")
