import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from tkseal.exceptions import TKSealError


class TK:
    """Wrapper for TK command line tool"""

    @staticmethod
    def exists() -> bool:
        """Check if TK executable is available in PATH"""
        return shutil.which('tk') is not None


class TKEnvironment:
    """Represents a Tanka environment and its configuration"""

    def __init__(self, path: str):
        """
        Initialize a Tanka environment from a path.

        Args:
            path: Path to Tanka environment directory or .jsonnet file

        Raises:
            TKSealError: If path is invalid or tk status fails
        """
        # Normalize path by removing trailing slash and .jsonnet extension
        self._path = re.sub(r'(\.jsonnet)?/?$', '', path)

        try:
            # Get and parse status output
            self._status_lines = self.status(self._path).splitlines()
            if not self._status_lines:
                raise TKSealError(
                    f"No status information found for path: {path}")
        except Exception as e:
            raise TKSealError(
                f"Failed to initialize Tanka environment: {str(e)}")

    @staticmethod
    def status(path: str) -> str:
        """
        Run 'tk status' command for the given path.

        Args:
            path: Path to Tanka environment

        Returns:
            str: Output from tk status command

        Raises:
            TKSealError: If tk command fails
        """
        try:
            result = subprocess.run(
                ["tk", "status", path],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise TKSealError(f"tk status failed: {e.stderr}")
        except Exception as e:
            raise TKSealError(f"Failed to run tk status: {str(e)}")

    @property
    def context(self) -> str:
        """Extract Kubernetes context from tk status output"""
        context = self._get_val("Context")
        if not context:
            raise TKSealError("Context not found in tk status output")
        return context

    @property
    def namespace(self) -> str:
        """Extract Kubernetes namespace from tk status output"""
        namespace = self._get_val("Namespace")
        if not namespace:
            raise TKSealError("Namespace not found in tk status output")
        return namespace

    def _get_val(self, key: str) -> Optional[str]:
        """
        Helper to extract values from tk status output lines.

        Args:
            key: The key to search for (e.g. "Context", "Namespace")

        Returns:
            Optional[str]: The value if found, None otherwise
        """
        pattern = rf"^\s*{key}:\s+(.+?)\s*$"
        for line in self._status_lines:
            if match := re.match(pattern, line):
                return match.group(1)
        return None
