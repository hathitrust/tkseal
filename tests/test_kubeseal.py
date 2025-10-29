import subprocess

import pytest

from tkseal.exceptions import TKSealError
from tkseal.kubeseal import KubeSeal


class TestKubeSeal:
    def test_kubeseal_exists_returns_true_when_installed(self, mocker):
        """Return True when kubectl is on PATH.
        This test mocks shutil.which to simulate kubectl being installed.
        """
        mock_which = mocker.patch("tkseal.kubeseal.shutil.which")
        mock_which.return_value = "/usr/local/bin/kubeseal"
        assert KubeSeal.exists() is True
        mock_which.assert_called_once_with("kubeseal")

    def test_kubeseal_exists_false_when_not_installed(self, mocker):
        """Return False when kubeseal is not on PATH."""

        mock_which = mocker.patch("tkseal.kubeseal.shutil.which")
        mock_which.return_value = None

        assert KubeSeal.exists() is False


class TestKubeSealSealing:
    """Tests for KubeSeal.seal() method."""

    def test_seal_calls_kubeseal_with_correct_args(self, mocker):
        """Test seal() invokes kubeseal with proper arguments."""
        # Mock subprocess.run
        mock_run = mocker.patch("tkseal.kubeseal.subprocess.run")
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

    def test_seal_returns_sealed_value(self, mocker):
        """Test seal() returns encrypted value from kubeseal."""
        # Mock successful kubeseal execution
        mock_run = mocker.patch("tkseal.kubeseal.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="AgBZ8Xn+encrypted+base64==",
            stderr="",
        )

        # Call seal and verify return value
        result = KubeSeal.seal(
            context="prod-cluster",
            namespace="default",
            name="app-secret",
            value="super-secret-password",
        )

        assert result == "AgBZ8Xn+encrypted+base64=="

    def test_seal_raises_error_on_kubeseal_failure(self, mocker):
        """Test seal() raises TKSealError when kubeseal fails."""
        # Mock kubeseal failure (non-zero exit code)
        mock_run = mocker.patch("tkseal.kubeseal.subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["kubeseal"],
            stderr="error: cannot fetch certificate: connection refused",
        )

        # Assert TKSealError is raised with meaningful message
        with pytest.raises(TKSealError) as exc_info:
            KubeSeal.seal(
                context="test-context",
                namespace="test-namespace",
                name="test-secret",
                value="plain-value",
            )

        assert "Command failed with exit code 1" in str(exc_info.value)
        assert "connection refused" in str(exc_info.value)

    def test_seal_handles_special_characters_in_value(self, mocker):
        """Test seal() properly handles special characters."""
        # Mock subprocess.run
        mock_run = mocker.patch("tkseal.kubeseal.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="sealed-special-chars", stderr=""
        )

        # Test with values containing quotes, newlines, etc.
        special_value = 'password"with\'quotes\nand\nnewlines'
        result = KubeSeal.seal(
            context="test-context",
            namespace="test-namespace",
            name="test-secret",
            value=special_value,
        )

        # Verify the special value was passed correctly via input parameter
        call_args = mock_run.call_args
        assert call_args.kwargs["input"] == special_value
        assert result == "sealed-special-chars"

    def test_seal_handles_generic_exception(self, mocker):
        """Test seal() handles unexpected exceptions."""
        # Mock subprocess.run to raise generic exception
        mock_run = mocker.patch("tkseal.kubeseal.subprocess.run")
        mock_run.side_effect = OSError("kubeseal binary not found")

        # Assert TKSealError is raised with meaningful message
        with pytest.raises(TKSealError) as exc_info:
            KubeSeal.seal(
                context="test-context",
                namespace="test-namespace",
                name="test-secret",
                value="plain-value",
            )

        assert "Failed to execute command" in str(exc_info.value)
        assert "kubeseal binary not found" in str(exc_info.value)
