"""SecretState manages state between local secret files and cluster secrets.

This module provides the SecretState class which coordinates access to:
- Local plain_secrets.json file
- Kubernetes cluster secrets via kubectl
- Tanka environment configuration
"""

import os
from pathlib import Path
from typing import cast

from tkseal import configuration
from tkseal.secret import ForbiddenSecret, Secrets
from tkseal.tk import TKEnvironment


def normalize_tk_env_path(path: str) -> str:
    """Normalize a Tanka environment path.

    Args:
        path: Path to normalize

    Returns:
        str: Normalized path without trailing slashes or .jsonnet extension
    """
    # Remove trailing slash
    path = os.path.normpath(path)
    # Remove trailing *.jsonnet file if present
    if path.endswith("main.jsonnet"):
        path = os.path.dirname(path)
    return path


class SecretState:
    """Manages secret state for a Tanka environment.

    SecretState provides access to both local plain secrets files and
    cluster secrets, along with the Tanka environment configuration.
    """

    def __init__(
        self,
        tk_env_path: str,
        plain_secrets_file_path: Path,
        sealed_secrets_file_path: Path,
        tk_env: TKEnvironment,
    ):
        """Initialize SecretState.

        Note: Use from_path() class method instead of calling this directly.

        Args:
            tk_env_path: Normalized path to Tanka environment
            plain_secrets_file_path: Path to plain_secrets.json file
            sealed_secrets_file_path: Path to sealed_secrets.json file
            tk_env: TKEnvironment instance for this environment
        """
        self.tk_env_path = tk_env_path
        self.plain_secrets_file_path = plain_secrets_file_path
        self.sealed_secrets_file_path = sealed_secrets_file_path
        self._tk_env = tk_env
        # Optional[Secrets] signifying the absence of the secrets_cache data until it is needed and loaded
        self._secrets_cache: Secrets | None = None  # Cache for the Secrets object

    @classmethod
    def from_path(cls, path: str) -> "SecretState":
        """Create SecretState from a Tanka environment path.

        This method normalizes the path by removing trailing slashes
        and .jsonnet extensions, then initializes the SecretState.

        Args:
            path: Path to Tanka environment directory or .jsonnet file

        Returns:
            SecretState: Initialized SecretState instance

        Raises:
            TKSealError: If the path is invalid or tk fails
        """
        # Normalize path: remove trailing slash and optional .jsonnet file
        # - trailing slash with optional word.jsonnet
        # We need to handle cases like:
        # - "/path/to/env/" -> "/path/to/env"
        # - "/path/to/env/main.jsonnet" -> "/path/to/env"
        # - "/path/to/env" -> "/path/to/env"

        normalized_path = normalize_tk_env_path(path)

        # Initialize TKEnvironment (will validate path exists)
        tk_env = TKEnvironment(normalized_path)

        # Construct file paths
        base_path = Path(normalized_path)
        # Using Pathlib we can easily join paths and get file names, parent directories, etc.
        plain_secrets_path = base_path / configuration.PLAIN_SECRETS_FILE
        sealed_secrets_path = base_path / configuration.SEALED_SECRETS_FILE

        return cls(
            tk_env_path=normalized_path,
            plain_secrets_file_path=plain_secrets_path,
            sealed_secrets_file_path=sealed_secrets_path,
            tk_env=tk_env,
        )

    @property
    def context(self) -> str:
        """Get Kubernetes context from TKEnvironment.

        Returns:
            str: Kubernetes context name
        """
        return self._tk_env.context

    @property
    def namespace(self) -> str:
        """Get Kubernetes namespace from TKEnvironment.

        Returns:
            str: Kubernetes namespace name
        """
        return self._tk_env.namespace

    def plain_secrets(self) -> str:
        """Read plain_secrets.json file contents.

        Returns:
            str: Contents of plain_secrets.json, or empty string if file
                 doesn't exist or cannot be read
        """
        try:
            return self.plain_secrets_file_path.read_text()
        except Exception:
            # Return empty string on any error (file not found, permission error, etc.)
            return ""

    def kube_secrets(self) -> str:
        """Get secrets from Kubernetes cluster.

        Returns:
            str: JSON string of secrets from the cluster

        Raises:
            TKSealError: If there's an error retrieving secrets from cluster
        """
        # Cache the Secrets object for access to forbidden_secrets and to avoid multiple cluster queries
        if self._secrets_cache is None:
            # Create Secrets object from the Tanka environment
            self._secrets_cache = Secrets.for_tk_env(self.tk_env_path)
        # Return the JSON representation of the secrets that is the entry point of other methods

        assert self._secrets_cache is not None
        return cast(str, self._secrets_cache.to_json())

    def get_forbidden_secrets(self) -> list[ForbiddenSecret]:
        """Get list of forbidden secrets that exist in the namespace but cannot be pulled.

        Returns:
            list[ForbiddenSecret]: List of a forbidden secret object.

        Note:
            This method requires kube_secrets() to be called first to populate the cache.
            If kube_secrets() hasn't been called, this will trigger a cluster query.
        """
        # Ensure secrets are loaded
        if self._secrets_cache is None:
            self.kube_secrets()  # This will populate _secrets_cache

        assert self._secrets_cache is not None
        return self._secrets_cache.forbidden_secrets
