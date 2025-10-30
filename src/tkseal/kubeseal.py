import shutil
import subprocess

from tkseal.exceptions import TKSealError


class KubeSeal:
    """Wrapper for kubeseal command line tool"""

    @staticmethod
    def exists() -> bool:
        """Return True if 'kubeseal' executable is available on PATH."""
        return shutil.which("kubeseal") is not None

    @staticmethod
    def seal(context: str, namespace: str, name: str, value: str) -> str:
        """Seal a secret value using kubeseal command-line utility.

        Args:
            context: Kubernetes context
            namespace: Kubernetes namespace
            name: Secret name
            value: Plain text value to seal

        Returns:
            str: Sealed (encrypted) value

        Raises:
            TKSealError: If kubeseal command fails
        """
        try:
            # Construct kubeseal command
            cmd = [
                "kubeseal",
                "--raw",
                "--namespace",
                namespace,
                "--name",
                name,
                "--context",
                context,
            ]

            # Execute kubeseal command with value piped via stdin
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
