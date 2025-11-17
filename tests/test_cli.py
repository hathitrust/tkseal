"""Test suite for TKSeal CLI commands."""

from tkseal.cli import cli
from tkseal.exceptions import TKSealError
from tkseal.secret import Secret


class TestVersionCommand:
    """Test cases for the version command."""

    def test_version_command_returns_version(self, cli_runner):
        """Test that version command returns the current version.
        - This simulates: $ tkseal version
        """

        result = cli_runner.invoke(cli, ["version"])

        assert result.exit_code == 0  # Command succeeded
        assert "1.0.0" in result.output  # Output contains version


class TestReadyCommand:
    """Test cases for the ready command."""

    def test_ready_command_all_dependencies_installed(
        self, cli_runner, mock_external_dependencies
    ):
        """Test that all dependencies are installed."""
        # Use the mock to replace Kubectl.exists()
        mock_kubeseal, mock_tk, mock_kubectl = mock_external_dependencies
        mock_kubectl.return_value = True
        mock_tk.return_value = True
        mock_kubeseal.return_value = True

        result = cli_runner.invoke(cli, ["ready"])

        assert result.exit_code == 0
        assert (
            "✅ Kubectl is installed" in result.output
        )  # This is the expected output of the function that checks if the tool exists
        assert "✅ tk is installed" in result.output
        assert "✅ Kubeseal is installed" in result.output

    def test_ready_command_whit_missing_kubeseal(
        self, cli_runner, mock_external_dependencies
    ):
        """Test that missing dependencies are installed."""

        mock_kubeseal, mock_tk, mock_kubectl = mock_external_dependencies
        mock_kubectl.return_value = True
        mock_tk.return_value = True
        mock_kubeseal.return_value = False

        result = cli_runner.invoke(cli, ["ready"])
        assert result.exit_code == 0
        assert "✅ Kubectl is installed" in result.output
        assert "✅ tk is installed" in result.output
        assert "❌ Kubeseal is NOT installed" in result.output


class TestDiffCommand:
    """Test cases for the diff command."""

    def test_diff_command_shows_differences(
        self, temp_tanka_env, mock_secret_state, cli_runner
    ):
        """Test diff command shows differences when secrets differ."""

        # Mock SecretState to return controlled data
        mock_secret_state.plain_secrets.return_value = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "new123"}\n  }\n]'
        mock_secret_state.kube_secrets.return_value = '[\n  {\n    "name": "app-secret",\n    "data": {"password": "old123"}\n  }\n]'

        result = cli_runner.invoke(cli, ["diff", str(temp_tanka_env)])

        assert result.exit_code == 0
        assert "old123" in result.output  # Shows old value
        assert "new123" in result.output  # Shows new value
        assert "-" in result.output or "+" in result.output  # Shows diff markers

    def test_diff_command_invalid_path(self, cli_runner):
        """Test diff command with non-existent path."""

        result = cli_runner.invoke(cli, ["diff", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()


class TestPullCommand:
    """Test cases for the pull command."""

    def test_pull_command_with_confirmation_accepted(
        self, cli_runner, mock_pull_cli, temp_tanka_env, mock_secret_state
    ):
        """Test pull command writes file when user confirms."""
        # Simulate 'y' response to confirmation
        result = cli_runner.invoke(cli, ["pull", str(temp_tanka_env)], input="y\n")

        assert result.exit_code == 0
        assert "plain_secrets.json" in result.output
        assert "Are you sure?" in result.output
        assert "Successfully pulled secrets" in result.output
        # Verify write was called
        mock_pull_cli.write.assert_called_once()

    def test_pull_command_with_confirmation_declined(
        self, cli_runner, mock_pull_cli, temp_tanka_env, mock_secret_state
    ):
        """Test pull command does not write when user declines."""
        # Simulate 'n' response to confirmation
        result = cli_runner.invoke(cli, ["pull", str(temp_tanka_env)], input="n\n")

        assert result.exit_code == 0
        assert "Are you sure?" in result.output
        # Verify write was NOT called
        mock_pull_cli.write.assert_not_called()
        assert "Successfully pulled" not in result.output

    def test_pull_command_no_differences(
        self,
        mocker,
        cli_runner,
        temp_tanka_env,
        mock_secret_state,
        diff_result_no_changes,
        mock_pull_cli,
    ):
        """Test pull command with no differences shows message and skips prompt."""
        # Override the ficture's mock_pull_cli to return no changes
        mock_pull_cli.run.return_value = diff_result_no_changes

        result = cli_runner.invoke(cli, ["pull", str(temp_tanka_env)])

        assert result.exit_code == 0
        assert "No differences" in result.output
        assert "Are you sure?" not in result.output
        # Verify write was NOT called
        mock_pull_cli.write.assert_not_called()

        # Assert: Should NOT show any warning messages because there are no forbidden secrets
        assert result.exit_code == 0
        assert "Warning" not in result.output
        assert "forbidden" not in result.output.lower()
        assert "cannot" not in result.output.lower()

    def test_pull_command_invalid_path(self, cli_runner):
        """Test pull command with non-existent path."""
        result = cli_runner.invoke(cli, ["pull", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()

    def test_pull_command_shows_warning_for_forbidden_secrets(
        self,
        cli_runner,
        mock_secret_state,
        mock_pull_cli,
        diff_result_no_changes,
        temp_tanka_env,
    ):
        """Test pull command shows warning when forbidden secrets are detected."""

        mock_secret_state.get_forbidden_secrets.return_value = [
            Secret(
                {
                    "metadata": {
                        "name": "default-token-abc",
                        "type": "kubernetes.io/service-account-token",
                    },
                    "data": {},
                }
            ),
            Secret(
                {
                    "metadata": {
                        "name": "service-account-token",
                        "type": "kubernetes.io/service-account-token",
                    },
                    "data": {},
                }
            ),
        ]

        mock_pull_cli.run.return_value = diff_result_no_changes
        result = cli_runner.invoke(cli, ["pull", str(temp_tanka_env)])

        # Assert: Should show warning about forbidden secrets
        assert result.exit_code == 0

        # Checking that both forbidden secrets are mentioned - multiple forbidden secrets
        assert "default-token-abc" in result.output
        assert "service-account-token" in result.output


class TestSealCommand:
    """Test cases for the seal command."""

    def test_seal_command_with_confirmation_accepted(
        self, cli_runner, temp_tanka_env, mock_secret_state, mock_seal_cli
    ):
        """Test seal command creates sealed secrets when user confirms."""
        # mock_secret_state already wired up via conftest fixture

        mock_seal, mock_diff = mock_seal_cli

        # Simulate 'y' response to confirmation
        result = cli_runner.invoke(cli, ["seal", str(temp_tanka_env)], input="y\n")

        assert result.exit_code == 0
        assert "sealed_secrets.json" in result.output
        assert "Are you sure?" in result.output
        assert "Successfully sealed secrets" in result.output
        # Verify Seal.run() was called
        mock_seal.run.assert_called_once()
        # Verify Diff.plain() was called
        # mock_diff.plain.assert_called_once()

    def test_seal_command_with_confirmation_declined(
        self, cli_runner, temp_tanka_env, mock_secret_state, mock_seal_cli
    ):
        """Test seal command does not seal when user declines."""
        # mock_secret_state already wired up via conftest fixture

        mock_seal, mock_diff = mock_seal_cli

        # Simulate 'n' response to confirmation
        result = cli_runner.invoke(cli, ["seal", str(temp_tanka_env)], input="n\n")

        assert result.exit_code == 0
        assert "Are you sure?" in result.output
        # Verify Seal.run() was NOT called
        mock_seal.run.assert_not_called()
        assert "Successfully sealed" not in result.output

    def test_seal_command_invalid_path(self, cli_runner):
        """Test seal command with non-existent path."""

        result = cli_runner.invoke(cli, ["seal", "/nonexistent/path"])

        # Click returns exit code 2 for usage errors (invalid arguments)
        assert result.exit_code == 2
        assert "does not exist" in result.output.lower()

    def test_seal_command_handles_tkseal_error(
        self, cli_runner, temp_tanka_env, mock_secret_state, mock_seal_cli
    ):
        """Test seal command handles TKSealError gracefully."""
        # mock_secret_state already wired up via conftest fixture

        mock_seal, mock_diff = mock_seal_cli

        # Mock Diff with differences
        mock_seal.run.side_effect = TKSealError("kubeseal command failed")

        result = cli_runner.invoke(cli, ["seal", str(temp_tanka_env)], input="y\n")

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "kubeseal command failed" in result.output


class TestFormatFlag:
    """Test cases for the --format flag on pull and seal commands."""

    def test_pull_command_with_yaml_format_flag(
        self, cli_runner, mock_pull_cli, temp_tanka_env, mock_secret_state
    ):
        """Test pull command with --format yaml creates .yaml file."""
        # Simulate 'y' response to confirmation
        result = cli_runner.invoke(
            cli, ["pull", str(temp_tanka_env), "--format", "yaml"], input="y\n"
        )

        assert result.exit_code == 0
        assert "plain_secrets.yaml" in result.output
        # Verify write was called
        mock_pull_cli.write.assert_called_once()

    def test_seal_command_with_yaml_format_flag(
        self, cli_runner, temp_tanka_env, mock_secret_state, mock_seal_cli
    ):
        """Test seal command with --format yaml creates .yaml file."""
        mock_seal, mock_diff = mock_seal_cli

        # Simulate 'y' response to confirmation
        result = cli_runner.invoke(
            cli, ["seal", str(temp_tanka_env), "--format", "yaml"], input="y\n"
        )

        assert result.exit_code == 0
        assert "sealed_secrets.yaml" in result.output
        # Verify Seal.run() was called
        mock_seal.run.assert_called_once()

    def test_invalid_format_flag_shows_error(self, cli_runner, temp_tanka_env):
        """Test that invalid --format value shows error."""
        result = cli_runner.invoke(
            cli, ["pull", str(temp_tanka_env), "--format", "xml"]
        )

        # Should fail with exit code 2 (usage error)
        assert result.exit_code == 2
        assert "Invalid value for '--format'" in result.output or "invalid choice" in result.output.lower()
