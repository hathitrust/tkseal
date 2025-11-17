import subprocess

from tkseal import TKSealError
from tkseal.serializers import get_serializer


def run_command(cmd: list[str], value: str = "") -> str:
    """Execute a kubectl command and return its output.

    Args:
        cmd: Command to execute as a list of strings
        value: Optional input value to pass via stdin

    Returns:
        The command output as a string

    Raises:
        TKSealError: If the command fails to execute or returns non-zero
    """
    try:
        result = subprocess.run(
            cmd, input=value, capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise TKSealError(
            f"Command failed with exit code {e.returncode}: {e.stderr}"
        ) from e
    except Exception as e:
        raise TKSealError(f"Failed to execute command: {str(e)}") from e


def normalize_to_json(content: str, source_format: str) -> str:
    """Normalize content to JSON format for comparison.

    This function is used to ensure consistent format when comparing secrets,
    regardless of whether they are stored as JSON or YAML.

    Args:
        content: String content in JSON or YAML format
        source_format: Format of the content ('json' or 'yaml')

    Returns:
        JSON string with consistent formatting

    Examples:
        >>> normalize_to_json('[]', 'json')
        '[]'
        >>> normalize_to_json('- name: test', 'yaml')
        '[{"name": "test"}]'
    """
    if not content or content.strip() == "" or content.strip() == "[]":
        return "[]"

    # Deserialize from source format, then serialize to JSON
    secret_serializer = get_serializer(source_format)
    data = secret_serializer.deserialize_secrets(content)
    return get_serializer("json").serialize_secrets(data)
