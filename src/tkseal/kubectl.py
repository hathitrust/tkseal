import shutil
import yaml

from tkseal.exceptions import TKSealError
from tkseal.tkseal_utils import run_command


class KubeCtl:
    """Wrapper for kubectl command line tool"""

    @staticmethod
    def exists() -> bool:
        """Return True if the 'kubectl' executable is available on PATH.
        Returns: bool
        """
        return shutil.which("kubectl") is not None

    @staticmethod
    def get_secrets(context: str, namespace: str) -> dict:
        """
        Fetch secrets from the Kubernetes cluster.

        Args:
            context: The kubectl context to use
            namespace: The namespace to fetch secrets from

        Returns:
            dict: Parsed YAML output of the secrets

        Raises:
            TKSealError: If there's an error running kubectl or parsing the output
        """
        # Construct kubectl command with proper context and namespace
        cmd = [
            "kubectl",
            f"--context={context}",
            f"--namespace={namespace}",
            "get",
            "secrets",
            "-o",
            "yaml",
        ]

        # Execute kubectl command and get output
        output = run_command(cmd)

        # Parse YAML output into Python dictionary
        try:
            return yaml.safe_load(output)
        except yaml.YAMLError as e:
            raise TKSealError(f"Failed to parse secrets YAML: {str(e)}") from e