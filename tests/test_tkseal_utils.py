import pytest
import subprocess

from tkseal.exceptions import TKSealError
from tkseal.kubectl import KubeCtl
from tkseal.kubeseal import KubeSeal

class TestTksealUtilsRunCommand:

    def test_seal_calls_kubeseal_with_correct_args(self, mocker):
        """Test seal() invokes kubeseal with proper arguments."""
        # Mock subprocess.run
        mock_run = mocker.patch("tkseal.tkseal_utils.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="sealed-value-123", stderr=""
        )

        # Call seal
        result = KubeSeal.seal(
            context="test-context",
            namespace="test-namespace",
            name="test-secret",
            value="plain-value",
        )

        # Verify kubeseal command was called with correct arguments
        mock_run.assert_called_once_with(
            [
                "kubeseal",
                "--raw",
                "--namespace",
                "test-namespace",
                "--name",
                "test-secret",
                "--context",
                "test-context",
            ],
            input="plain-value",
            capture_output=True,
            text=True,
            check=True,
        )
        assert result == "sealed-value-123"

    def test_get_secrets_kubectl_error(self, mocker):
        mock_run = mocker.patch("tkseal.tkseal_utils.run_command")

        mock_run.side_effect = TKSealError("Command failed with exit code 1: kubectl error")

        # Test that TKSealError is raised when kubectl command fails
        with pytest.raises(TKSealError) as exc_info:
            KubeCtl.get_secrets("test-context", "test-namespace")

        assert "Command failed" in str(exc_info.value)


