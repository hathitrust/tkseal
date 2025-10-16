import pytest
from tkseal.kubeseal import KubeSeal


class TestKubeSeal:
    def test_kubeseal_exists_returns_true_when_installed(self, mocker):
        """Return True when kubectl is on PATH.
        This test mocks shutil.which to simulate kubectl being installed.
        """
        mock_which = mocker.patch("tkseal.kubectl.shutil.which")
        mock_which.return_value = "/usr/local/bin/kubeseal"
        assert KubeSeal.exists() is True
        mock_which.assert_called_once_with("kubeseal")

    def test_kubeseal_exists_false_when_not_installed(self, mocker):
        """Return False when kubeseal is not on PATH."""

        mock_which = mocker.patch("tkseal.kubectl.shutil.which")
        mock_which.return_value = None

        assert KubeSeal.exists() is False