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

    def test_diff_command_shows_differences(self, temp_tanka_env, mock_secret_state):
        """Test diff command shows differences when secrets differ."""

        # Mock SecretState to return controlled data
        mock_secret_state.plain_secrets.return_value = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "new123"}\n  }\n]'
        mock_secret_state.kube_secrets.return_value = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "old123"}\n  }\n]'

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(temp_tanka_env)])

        assert result.exit_code == 0
        assert "old123" in result.output  # Shows old value
        assert "new123" in result.output  # Shows new value
        assert "-" in result.output or "+" in result.output  # Shows diff markers

    def test_diff_command_no_differences(self, temp_tanka_env, mock_secret_state):
        """Test diff command shows 'No differences' when secrets are identical."""

        # Mock SecretState with identical secrets
        identical_secrets = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "same123"}\n  }\n]'
        mock_secret_state.plain_secrets.return_value = identical_secrets
        mock_secret_state.kube_secrets.return_value = identical_secrets

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(temp_tanka_env)])

        assert result.exit_code == 0
        assert "No differences" in result.output

    def test_diff_command_invalid_path(self):
        """Test diff command with non-existent path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["diff", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()

    def test_diff_command_secret_state_creation_failure(self, mocker, temp_tanka_env):
        """Test diff command handles SecretState creation failure gracefully."""

        # Mock SecretState.from_path to raise TKSealError
        mocker.patch(
            "tkseal.cli.SecretState.from_path",
            side_effect=TKSealError("Failed to initialize Tanka environment"),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["diff", str(temp_tanka_env)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Failed to initialize Tanka environment" in result.output


class TestPullCommand:
    """Test cases for the pull command."""

    def test_pull_command_with_confirmation_accepted(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test pull command writes file when user confirms."""
        # mock_secret_state already wired up via conftest fixture
        # temp_tanka_env already created and populated

        # Mock Pull instance
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        # Simulate 'y' response to confirmation
        result = runner.invoke(cli, ["pull", str(temp_tanka_env)], input="y\n")

        assert result.exit_code == 0
        assert "plain_secrets.json" in result.output
        assert "Are you sure?" in result.output
        assert "Successfully pulled secrets" in result.output
        # Verify write was called
        mock_pull.write.assert_called_once()

    def test_pull_command_with_confirmation_declined(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test pull command does not write when user declines."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Pull instance
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        # Simulate 'n' response to confirmation
        result = runner.invoke(cli, ["pull", str(temp_tanka_env)], input="n\n")

        assert result.exit_code == 0
        assert "Are you sure?" in result.output
        # Verify write was NOT called
        mock_pull.write.assert_not_called()
        assert "Successfully pulled" not in result.output

    def test_pull_command_no_differences(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test pull command with no differences shows message and skips prompt."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Pull instance with no differences
        mock_pull = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_pull.run.return_value = DiffResult(has_differences=False, diff_output="")
        mocker.patch("tkseal.cli.Pull", return_value=mock_pull)

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(temp_tanka_env)])

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

    def test_pull_command_secret_state_creation_failure(self, mocker, temp_tanka_env):
        """Test pull command handles SecretState creation failure gracefully."""

        # Override the conftest mock to raise an error for this specific test
        mocker.patch(
            "tkseal.cli.SecretState.from_path",
            side_effect=TKSealError("Failed to initialize Tanka environment"),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["pull", str(temp_tanka_env)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Failed to initialize Tanka environment" in result.output


class TestSealCommand:
    """Test cases for the seal command."""

    def test_seal_command_with_confirmation_accepted(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test seal command creates sealed secrets when user confirms."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Diff instance to show differences
        mock_diff = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_diff.plain.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

        # Mock Seal instance
        mock_seal = mocker.Mock()
        mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

        runner = CliRunner()
        # Simulate 'y' response to confirmation
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)], input="y\n")

        assert result.exit_code == 0
        assert "sealed_secrets.json" in result.output
        assert "Are you sure?" in result.output
        assert "Successfully sealed secrets" in result.output
        # Verify Seal.run() was called
        mock_seal.run.assert_called_once()
        # Verify Diff.plain() was called
        mock_diff.plain.assert_called_once()

    def test_seal_command_with_confirmation_declined(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test seal command does not seal when user declines."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Diff instance to show differences
        mock_diff = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_diff.plain.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

        # Mock Seal instance
        mock_seal = mocker.Mock()
        mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

        runner = CliRunner()
        # Simulate 'n' response to confirmation
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)], input="n\n")

        assert result.exit_code == 0
        assert "Are you sure?" in result.output
        # Verify Seal.run() was NOT called
        mock_seal.run.assert_not_called()
        assert "Successfully sealed" not in result.output

    def test_seal_command_no_differences(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test seal command with no differences skips sealing."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Diff instance with no differences
        mock_diff = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_diff.plain.return_value = DiffResult(has_differences=False, diff_output="")
        mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

        # Mock Seal instance
        mock_seal = mocker.Mock()
        mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

        runner = CliRunner()
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)])

        assert result.exit_code == 0
        assert "No differences" in result.output
        assert "Are you sure?" not in result.output
        # Verify Seal.run() was NOT called
        mock_seal.run.assert_not_called()

    def test_seal_command_shows_diff_before_prompt(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test seal command shows diff output before asking confirmation."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Diff with specific diff output
        mock_diff = mocker.Mock()
        from tkseal.diff import DiffResult

        test_diff_output = "--- cluster\n+++ plain_secrets.json\n-old_value\n+new_value"
        mock_diff.plain.return_value = DiffResult(
            has_differences=True, diff_output=test_diff_output
        )
        mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

        # Mock Seal instance
        mock_seal = mocker.Mock()
        mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

        runner = CliRunner()
        # Decline confirmation to verify diff was shown
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)], input="n\n")

        assert result.exit_code == 0
        # Verify diff output is shown before prompt
        assert "old_value" in result.output
        assert "new_value" in result.output
        assert "Are you sure?" in result.output
        # Verify the order: diff comes before prompt
        diff_position = result.output.find("old_value")
        prompt_position = result.output.find("Are you sure?")
        assert diff_position < prompt_position

    def test_seal_command_shows_warning_message(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test seal command shows yellow warning message."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Diff with differences
        mock_diff = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_diff.plain.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

        # Mock Seal instance
        mock_seal = mocker.Mock()
        mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

        runner = CliRunner()
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)], input="n\n")

        assert result.exit_code == 0
        # Verify warning message is shown
        assert (
            'This shows what would change in the cluster based on "plain_secrets.json"'
            in result.output
        )

    def test_seal_command_invalid_path(self):
        """Test seal command with non-existent path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["seal", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()

    def test_seal_command_handles_tkseal_error(
        self, mocker, temp_tanka_env, mock_secret_state
    ):
        """Test seal command handles TKSealError gracefully."""
        # mock_secret_state already wired up via conftest fixture

        # Mock Diff with differences
        mock_diff = mocker.Mock()
        from tkseal.diff import DiffResult

        mock_diff.plain.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

        # Mock Seal to raise TKSealError
        mock_seal = mocker.Mock()
        mock_seal.run.side_effect = TKSealError("kubeseal command failed")
        mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

        runner = CliRunner()
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)], input="y\n")

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "kubeseal command failed" in result.output

    def test_seal_command_secret_state_creation_failure(self, mocker, temp_tanka_env):
        """Test seal command handles SecretState creation failure gracefully."""
        # Override the conftest mock to raise an error
        mocker.patch(
            "tkseal.cli.SecretState.from_path",
            side_effect=TKSealError("Failed to initialize Tanka environment"),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["seal", str(temp_tanka_env)])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Failed to initialize Tanka environment" in result.output
