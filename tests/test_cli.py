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

    def test_ready_command_whit_missing_kubeseal(self, mocker):
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

        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(env_path)])

        assert result.exit_code == 0
        assert "old123" in result.output  # Shows old value
        assert "new123" in result.output  # Shows new value
        assert "-" in result.output or "+" in result.output  # Shows diff markers

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

        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

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

        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(env_path)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "kubectl command failed" in result.output


class TestPullCommand:
    """Test cases for the pull command."""

    def test_pull_command_with_confirmation_accepted(self, mocker, tmp_path):
        """Test pull command writes file when user confirms."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState
        mock_secret_state = mocker.Mock()
        mock_secret_state.plain_secrets_file_path = env_path / "plain_secrets.json"

        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        # Mock Pull instance
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        # Simulate 'y' response to confirmation
        result = runner.invoke(cli, ["pull", str(env_path)], input="y\n")

        assert result.exit_code == 0
        assert "plain_secrets.json" in result.output
        assert "Are you sure?" in result.output
        assert "Successfully pulled secrets" in result.output
        # Verify write was called
        mock_pull.write.assert_called_once()

    def test_pull_command_with_confirmation_declined(self, mocker, tmp_path):
        """Test pull command does not write when user declines."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState
        mock_secret_state = mocker.Mock()
        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        # Mock Pull instance
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        # Simulate 'n' response to confirmation
        result = runner.invoke(cli, ["pull", str(env_path)], input="n\n")

        assert result.exit_code == 0
        assert "Are you sure?" in result.output
        # Verify write was NOT called
        mock_pull.write.assert_not_called()
        assert "Successfully pulled" not in result.output

    def test_pull_command_no_differences(self, mocker, tmp_path):
        """Test pull command with no differences shows message and skips prompt."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState
        mock_secret_state = mocker.Mock()
        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        # Mock Pull instance with no differences
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(has_differences=False, diff_output="")
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(env_path)])

        assert result.exit_code == 0
        assert "No differences" in result.output
        assert "Are you sure?" not in result.output
        # Verify write was NOT called
        mock_pull.write.assert_not_called()

    def test_pull_command_invalid_path(self):
        """Test pull command with non-existent path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["pull", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()

    def test_pull_command_secret_state_creation_failure(self, mocker, tmp_path):
        """Test pull command handles SecretState creation failure gracefully."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState.from_path to raise TKSealError
        mocker.patch(
            "tkseal.cli.SecretState.from_path",
            side_effect=TKSealError("Failed to initialize Tanka environment"),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(env_path)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Failed to initialize Tanka environment" in result.output

    def test_pull_command_file_write_verification(self, mocker, tmp_path):
        """Test that pulled secrets are written correctly to file."""
        # Create a temporary Tanka environment with actual file
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)
        secrets_file = env_path / "plain_secrets.json"

        # Create a real SecretState mock that writes to real file
        mock_secret_state = mocker.Mock()
        mock_secret_state.plain_secrets_file_path = secrets_file
        mock_secret_state.kube_secrets.return_value = '{"test": "data"}'

        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        # Use real Pull class but mock the diff result
        from tkseal.pull import Pull

        real_pull = Pull(mock_secret_state)

        # Mock only the run method to return differences
        from tkseal.diff import DiffResult

        mocker.patch.object(
            real_pull,
            "run",
            return_value=DiffResult(has_differences=True, diff_output="+new"),
        )
        mocker.patch("tkseal.cli.Pull", return_value=real_pull)

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(env_path)], input="y\n")

        assert result.exit_code == 0
        assert secrets_file.exists()
        assert secrets_file.read_text() == '{"test": "data"}'

    def test_pull_command_kubectl_error(self, mocker, tmp_path):
        """Test pull command handles kubectl errors gracefully."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState
        mock_secret_state = mocker.Mock()
        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        # Mock Pull.run() to raise TKSealError
        mock_pull = mocker.Mock()
        mock_pull.run.side_effect = TKSealError("kubectl command failed")
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(env_path)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "kubectl command failed" in result.output

    def test_pull_command_shows_warning_message(self, mocker, tmp_path):
        """Test pull command displays yellow warning message."""
        # Create a temporary Tanka environment
        env_path = tmp_path / "environments" / "test-env"
        env_path.mkdir(parents=True)

        # Mock SecretState
        mock_secret_state = mocker.Mock()
        mocker.patch("tkseal.cli.SecretState.from_path", return_value=mock_secret_state)

        # Mock Pull instance with no differences
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(has_differences=False, diff_output="")
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(env_path)])

        assert result.exit_code == 0
        assert "plain_secrets.json" in result.output
        assert "Kubernetes cluster" in result.output
