import shutil
import subprocess

import yaml

from tkseal.exceptions import TKSealError


class KubeCtl:
    """Wrapper for kubectl command line tool"""

    @staticmethod
    def exists() -> bool:
        """Return True if the 'kubectl' executable is available on PATH."""
        return shutil.which("kubectl") is not None

    @staticmethod
    def _run_command(cmd: list[str]) -> str:
        """Execute a kubectl command and return its output.

        Args:
            cmd: Command to execute as a list of strings

        Returns:
            The command output as a string

        Raises:
            TKSealError: If the command fails to execute or returns non-zero
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise TKSealError(
                f"Command failed with exit code {e.returncode}: {e.stderr}")
        except Exception as e:
            raise TKSealError(f"Failed to execute command: {str(e)}")

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
        try:
            cmd = ["kubectl", f"--context={context}",
                   f"--namespace={namespace}", "get", "secrets", "-o", "yaml"]
            output = KubeCtl._run_command(cmd)

            try:
                return yaml.safe_load(output)
            except yaml.YAMLError as e:
                raise TKSealError(f"Failed to parse secrets YAML: {str(e)}")

        except Exception as e:
            raise TKSealError(f"Failed to get secrets: {str(e)}")
        except Exception as e:
            raise TKSealError(f"Failed to get secrets: {str(e)}")
