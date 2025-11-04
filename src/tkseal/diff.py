"""Diff module for comparing local and cluster secrets."""

import difflib
from dataclasses import dataclass

from tkseal.configuration import PLAIN_SECRETS_FILE
from tkseal.secret_state import SecretState


@dataclass
class DiffResult:
    """Result of a diff operation."""

    has_differences: bool
    diff_output: str


class Diff:
    """Handles comparison between local and cluster secrets."""

    def __init__(self, secret_state: SecretState):
        """Initialize Diff with a SecretState instance."""
        self.secret_state = secret_state

    def plain(self) -> DiffResult:
        """Compare showing what would change in the cluster (push mode)."""
        kube_secrets = self.secret_state.kube_secrets()
        plain_secrets = self.secret_state.plain_secrets()

        return self._generate_diff(
            from_text=kube_secrets,
            to_text=plain_secrets,
            from_label="cluster",
            to_label=PLAIN_SECRETS_FILE,
        )

    def pull(self) -> DiffResult:
        """Compare showing what pulling would change locally (pull mode).
        This function is only used for displaying diffs when pulling secrets
        """
        plain_secrets = self.secret_state.plain_secrets()
        kube_secrets = self.secret_state.kube_secrets()

        return self._generate_diff(
            from_text=plain_secrets,
            to_text=kube_secrets,
            from_label=PLAIN_SECRETS_FILE,
            to_label="cluster",
        )

    def _generate_diff(
        self, from_text: str, to_text: str, from_label: str, to_label: str
    ) -> DiffResult:
        """Generate unified diff between two texts."""
        # Split into lines for difflib
        from_lines = from_text.splitlines(keepends=True)
        to_lines = to_text.splitlines(keepends=True)

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                from_lines,
                to_lines,
                fromfile=from_label,
                tofile=to_label,
                lineterm="",
            )
        )

        # Check if there are any differences
        if not diff_lines:
            return DiffResult(has_differences=False, diff_output="")

        # Join diff lines into a single string
        diff_output = "\n".join(diff_lines)
        return DiffResult(has_differences=True, diff_output=diff_output)
