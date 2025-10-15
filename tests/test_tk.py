import subprocess
from unittest.mock import Mock, patch

import pytest

from tkseal.exceptions import TKSealError
from tkseal.tk import TK, TKEnvironment


class TestTK:
    @patch("tkseal.tk.shutil.which", return_value="/usr/local/bin/tk")
    def test_tk_exists_returns_true_when_installed(self, mock_which):
        """Return True when tk is on PATH."""
        assert TK.exists() is True
        mock_which.assert_called_once_with("tk")

    @patch("tkseal.tk.shutil.which", return_value=None)
    def test_tk_exists_false_when_not_installed(self, _):
        """Return False when tk is not on PATH."""
        assert TK.exists() is False


class TestTKEnvironment:
    @patch.object(TKEnvironment, 'status')
    def test_tk_environment_initialization(self, mock_status):
        """Test TKEnvironment initialization with various path formats"""
        mock_status.return_value = """
        Context:    test-context
        Namespace:  test-namespace
        """
        paths = [
            "/path/to/env",
            "/path/to/env/",
            "/path/to/env.jsonnet",
            "/path/to/env.jsonnet/"
        ]

        for path in paths:
            env = TKEnvironment(path)
            assert env.context == "test-context"
            assert env.namespace == "test-namespace"

    @patch('subprocess.run')
    def test_tk_environment_status_command(self, mock_run):
        """Test tk status command execution"""
        mock_process = Mock()
        mock_process.stdout = "Context: test-context\nNamespace: test-namespace"
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        status = TKEnvironment.status("/path/to/env")
        assert "Context: test-context" in status
        assert "Namespace: test-namespace" in status

    @patch.object(TKEnvironment, 'status')
    def test_tk_environment_invalid_status(self, mock_status):
        """Test error handling for invalid tk status output"""
        mock_status.return_value = "Invalid output"

        with pytest.raises(TKSealError) as exc_info:
            env = TKEnvironment("/path/to/env")
            _ = env.context
        assert "Context not found" in str(exc_info.value)

    @patch('subprocess.run')
    def test_tk_environment_command_failure(self, mock_run):
        """Test error handling for tk command failure"""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ['tk'], stderr="Command failed")

        with pytest.raises(TKSealError) as exc_info:
            TKEnvironment("/path/to/env")
        assert "tk status failed" in str(exc_info.value)

    @patch.object(TKEnvironment, 'status')
    def test_get_val_with_spaces(self, mock_status):
        """Test _get_val handles values with spaces correctly"""
        mock_status.return_value = """
        Context:    my-cluster context
        Namespace:  my-app namespace
        """
        env = TKEnvironment("/path/to/env")
        assert env._get_val("Context") == "my-cluster context"
        assert env._get_val("Namespace") == "my-app namespace"

    @patch.object(TKEnvironment, 'status')
    def test_get_val_missing_key(self, mock_status):
        """Test _get_val returns None for missing keys"""
        mock_status.return_value = "Context: test-context"
        env = TKEnvironment("/path/to/env")
        assert env._get_val("NonexistentKey") is None
