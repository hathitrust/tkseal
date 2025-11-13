import pytest

from tkseal.exceptions import TKSealError
from tkseal.tk import TK, TKEnvironment


class TestTK:
    def test_tk_exists_returns_true_when_installed(self, mocker):
        """Return True when tk is on PATH."""

        mock_which = mocker.patch(
            "tkseal.tk.shutil.which", return_value="/usr/local/bin/tk"
        )

        assert TK.exists() is True
        mock_which.assert_called_once_with("tk")

    def test_tk_exists_false_when_not_installed(self, mocker):
        """Return False when tk is not on PATH."""
        mocker_which = mocker.patch("tkseal.tk.shutil.which")
        mocker_which.return_value = None

        assert TK.exists() is False


class TestTKEnvironment:
    def test_tk_environment_initialization(self, mocker):
        """Test TKEnvironment initialization with various path formats"""
        mock_status = mocker.patch("tkseal.tk.TKEnvironment.status")

        mock_status.return_value = """
        Context:    test-context
        Namespace:  test-namespace
        """
        paths = [
            "/path/to/env",
            "/path/to/env/",
            "/path/to/env.jsonnet",
            "/path/to/env.jsonnet/",
        ]

        for path in paths:
            env = TKEnvironment(path)
            assert env.context == "test-context"
            assert env.namespace == "test-namespace"

    def test_tk_environment_status_command(self, mocker):
        """Test tk status command execution"""

        mock_run = mocker.patch("subprocess.run")

        mock_process = mocker.Mock()
        mock_process.stdout = "Context: test-context\nNamespace: test-namespace"
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        status = TKEnvironment.status("/path/to/env")
        assert "Context: test-context" in status
        assert "Namespace: test-namespace" in status

    def test_tk_environment_invalid_status(self, mocker):
        """Test error handling for invalid tk status output"""

        mock_status = mocker.patch("tkseal.tk.TKEnvironment.status")

        mock_status.return_value = "Invalid output"

        with pytest.raises(TKSealError) as exc_info:
            env = TKEnvironment("/path/to/env")
            _ = env.context
        assert "Context not found" in str(exc_info.value)

    def test_tk_environment_command_failure(self, mocker):
        """Test error handling for tk command failure"""

        mock_run = mocker.patch("tkseal.tk.run_command")

        mock_run.side_effect = TKSealError("Command failed with exit code 1: tk error")

        with pytest.raises(TKSealError) as exc_info:
            TKEnvironment("/path/to/env")
        assert "Command failed" in str(exc_info.value)

    def test_get_val_with_spaces(self, mocker):
        """Test _get_val handles values with spaces correctly"""

        mock_status = mocker.patch("tkseal.tk.TKEnvironment.status")

        mock_status.return_value = """
                Context:    my-cluster context
                Namespace:  my-app namespace
                """
        tk_environment = TKEnvironment("/path/to/env")
        assert tk_environment.context == "my-cluster context"
        assert tk_environment.namespace == "my-app namespace"

    def test_get_val_missing_key(self, mocker, tk_status_file):
        """Test _get_val returns None for missing keys"""

        mock_status = mocker.patch("tkseal.tk.TKEnvironment.status")

        mock_status.return_value = tk_status_file.read_text()
        env = TKEnvironment("/path/to/env")
        assert env._get_val("NonexistentKey") == ""
