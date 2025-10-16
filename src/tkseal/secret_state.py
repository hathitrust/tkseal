import json
import re
from pathlib import Path
from typing import Optional

from tkseal.exceptions import TKSealError
from tkseal.secret import Secrets
from tkseal.tk import TKEnvironment

# Configuration constants for secret file paths
PLAIN_SECRETS_FILE = "plain_secrets.json"
SEALED_SECRETS_FILE = "sealed_secrets.json"


class SecretState:
    """
    Coordinates state between local secret files and Kubernetes cluster secrets.

    This class manages the interaction between local plain/sealed secret files
    and the corresponding secrets in a Kubernetes cluster, providing access
    to both local and cluster state.
    """

    def __init__(self, tk_env_path: str) -> None:
        """
        Initialize SecretState for a Tanka environment path.

        Args:
            tk_env_path: Path to Tanka environment directory or .jsonnet file

        Raises:
            TKSealError: If the path is invalid or Tanka environment cannot be loaded
        """
        # Normalize path by removing trailing slash and .jsonnet extension
        print(f"Original Path: {tk_env_path}")
        self._path = re.sub(r'(\.jsonnet)?/?$', '', tk_env_path)

        try:
            # Create Tanka environment instance
            self._tk_env = TKEnvironment(self._path)
            print(f"Normalized Path: {self._path}")

            # Set up paths for secret files
            base_path = Path(self._path)
            self._plain_secrets_file_path = base_path / PLAIN_SECRETS_FILE
            self._sealed_secrets_file_path = base_path / SEALED_SECRETS_FILE

        except Exception as e:
            raise TKSealError(f"Failed to initialize secret state: {str(e)}")

    @property
    def context(self) -> str:
        """
        Get Kubernetes context from Tanka environment.

        Returns:
            str: The Kubernetes context name

        Raises:
            TKSealError: If context cannot be retrieved
        """
        return self._tk_env.context

    @property
    def namespace(self) -> str:
        """
        Get Kubernetes namespace from Tanka environment.

        Returns:
            str: The Kubernetes namespace name

        Raises:
            TKSealError: If namespace cannot be retrieved
        """
        return self._tk_env.namespace

    @property
    def plain_secrets(self) -> str:
        """
        Read plain secrets from local JSON file.

        Returns:
            str: JSON string of plain secrets, or empty string if file doesn't exist

        Raises:
            TKSealError: If file exists but cannot be read or parsed
        """
        if not self._plain_secrets_file_path.exists():
            return ""

        try:
            return self._plain_secrets_file_path.read_text()
        except Exception as e:
            raise TKSealError(
                f"Failed to read plain secrets file: {str(e)}")

    @property
    def kube_secrets(self) -> str:
        """
        Get current secrets from Kubernetes cluster.

        Returns:
            str: JSON string representation of cluster secrets

        Raises:
            TKSealError: If cluster secrets cannot be retrieved or processed
        """
        try:
            secrets = Secrets.for_tk_env(self._path)
            return secrets.to_json()
        except Exception as e:
            raise TKSealError(
                f"Failed to get secrets from cluster: {str(e)}")
