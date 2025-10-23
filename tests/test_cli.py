"""Test suite for TKSeal CLI commands."""

from click.testing import (
    CliRunner,
)  # is Click's built-in test utility that simulates running CLI commands in isolation

from tkseal.cli import cli
from tkseal.exceptions import TKSealError


class TestVersionCommand:
    """Test cases for the version command."""

    def test_version_command_returns_version(self):
        """Test that version command returns the current version."""
        runner = CliRunner()
        # This simulates: $ tkseal version
        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0  # Command succeeded
        assert "1.0.0" in result.output  # Output contains version


class TestReadyCommand:
    """Test cases for the ready command."""

    def test_ready_command_all_dependencies_installed(self, mocker):
        """Test that all dependencies are installed."""
        # Use the mock to replace Kubectl.exists()

        mock_kubeseal = mocker.patch("tkseal.kubeseal.KubeSeal.exists")
        mock_tk = mocker.patch("tkseal.tk.TK.exists")
        mock_kubectl = mocker.patch("tkseal.kubectl.KubeCtl.exists")

        mock_kubectl.return_value = True
        mock_tk.return_value = True
        mock_kubeseal.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["ready"])
        assert result.exit_code == 0
        assert (
            "✅ Kubectl is installed" in result.output
        )  # This is the expected output of the function that check if the tool exist
        assert "✅ tk is installed" in result.output
        assert "✅ Kubeseal is installed" in result.output

    def test_ready_command_missing_dependencies_installed(self, mocker):
        """Test that missing dependencies are installed."""

        mock_kubeseal = mocker.patch("tkseal.kubeseal.KubeSeal.exists")
        mock_tk = mocker.patch("tkseal.tk.TK.exists")
        mock_kubectl = mocker.patch("tkseal.kubectl.KubeCtl.exists")

        mock_kubectl.return_value = True
        mock_tk.return_value = True
        mock_kubeseal.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["ready"])
        assert result.exit_code == 0
        assert "✅ Kubectl is installed" in result.output
        assert "✅ tk is installed" in result.output
        assert "❌ Kubeseal is NOT installed" in result.output

        runner = CliRunner()
        result = runner.invoke(cli, ["ready"])
        assert result.exit_code == 0


class TestDiffCommand:
    """Test cases for the diff command."""

    def test_diff_command_shows_differences(self, mocker, tmp_path):
        """Test diff command shows differences when secrets differ."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState to return controlled data
        mock_secret_state = mocker.Mock()
        mock_secret_state.plain_secrets.return_value = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "new123"}\n  }\n]'
        mock_secret_state.kube_secrets.return_value = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "old123"}\n  }\n]'

        mocker.patch(
            "tkseal.cli.SecretState.from_path", return_value=mock_secret_state
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(env_path)])

        assert result.exit_code == 0
        assert "old123" in result.output  # Shows old value
        assert "new123" in result.output  # Shows new value
        assert ("-" in result.output or "+" in result.output)  # Shows diff markers

    def test_diff_command_no_differences(self, mocker, tmp_path):
        """Test diff command shows 'No differences' when secrets are identical."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState with identical secrets
        mock_secret_state = mocker.Mock()
        identical_secrets = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "same123"}\n  }\n]'
        mock_secret_state.plain_secrets.return_value = identical_secrets
        mock_secret_state.kube_secrets.return_value = identical_secrets

        mocker.patch(
            "tkseal.cli.SecretState.from_path", return_value=mock_secret_state
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(env_path)])

        assert result.exit_code == 0
        assert "No differences" in result.output

    def test_diff_command_invalid_path(self):
        """Test diff command with non-existent path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["diff", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()

    def test_diff_command_secret_state_creation_failure(self, mocker, tmp_path):
        """Test diff command handles SecretState creation failure gracefully."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState.from_path to raise TKSealError
        mocker.patch(
            "tkseal.cli.SecretState.from_path",
            side_effect=TKSealError("Failed to initialize Tanka environment"),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(env_path)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Failed to initialize Tanka environment" in result.output

    def test_diff_command_kubectl_error(self, mocker, tmp_path):
        """Test diff command handles kubectl errors gracefully."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState that raises error when accessing kube_secrets
        mock_secret_state = mocker.Mock()
        mock_secret_state.kube_secrets.side_effect = TKSealError(
            "kubectl command failed"
        )

        mocker.patch(
            "tkseal.cli.SecretState.from_path", return_value=mock_secret_state
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(env_path)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "kubectl command failed" in result.output
