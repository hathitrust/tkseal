import subprocess

from tkseal import TKSealError


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
