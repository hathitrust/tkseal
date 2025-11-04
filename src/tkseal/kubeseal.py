import shutil
import subprocess

from tkseal.exceptions import TKSealError
from tkseal.tkseal_utils import run_command


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

        """
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
        result = run_command(cmd, value=value)

        return result