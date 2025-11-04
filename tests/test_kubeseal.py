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

    def test_seal_returns_sealed_value(self, mocker):
        """Test seal() returns encrypted value from kubeseal."""
        # Mock successful kubeseal execution
        mock_run = mocker.patch("tkseal.kubeseal.run_command")
        mock_run.return_value = "AgBZ8Xn+encrypted+base64=="

        # Call seal and verify return value
        result = KubeSeal.seal(
            context="prod-cluster",
            namespace="default",
            name="app-secret",
            value="super-secret-password",
        )

        assert result == "AgBZ8Xn+encrypted+base64=="

    def test_seal_handles_special_characters_in_value(self, mocker):
        """Test seal() properly handles special characters."""
        # Mock subprocess.run
        mock_run = mocker.patch("tkseal.kubeseal.run_command")
        mock_run.return_value = "sealed-special-chars"

        # Test with values containing quotes, newlines, etc.
        special_value = "password\"with'quotes\nand\nnewlines"
        result = KubeSeal.seal(
            context="test-context",
            namespace="test-namespace",
            name="test-secret",
            value=special_value,
        )

        # Verify the special value was passed correctly via input parameter
        call_args = mock_run.call_args
        assert call_args.kwargs["value"] == special_value
        assert result == "sealed-special-chars"


