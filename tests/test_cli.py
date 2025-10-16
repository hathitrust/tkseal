"""Test suite for TKSeal CLI commands."""

import pytest
from click.testing import CliRunner # is Click's built-in test utility that simulates running CLI commands in isolation
from tkseal.cli import cli


class TestVersionCommand:
    """Test cases for the version command."""

    def test_version_command_returns_version(self):
        """Test that version command returns the current version."""
        runner = CliRunner()
        # This simulates: $ tkseal version
        result = runner.invoke(cli, ['version'])

        assert result.exit_code == 0 # Command succeeded
        assert "1.0.0" in result.output # Output contains version

class TestReadyCommand:
    """Test cases for the ready command."""

    def test_ready_command_all_dependencies_installed(self, mocker):
        """Test that all dependencies are installed."""
        # Use the mock to replace Kubectl.exists()

        mock_kubeseal = mocker.patch('tkseal.kubeseal.KubeSeal.exists')
        mock_tk = mocker.patch('tkseal.tk.TK.exists')
        mock_kubectl = mocker.patch('tkseal.kubectl.KubeCtl.exists')

        mock_kubectl.return_value = True
        mock_tk.return_value = True
        mock_kubeseal.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ['ready'])
        assert result.exit_code == 0
        assert "✅ Kubectl is installed" in result.output # This is the expected output of the function that check if the tool exist
        assert "✅ tk is installed" in result.output
        assert "✅ Kubeseal is installed" in result.output

    def test_ready_command_missing_dependencies_installed(self,mocker):
        """Test that missing dependencies are installed."""

        mock_kubeseal = mocker.patch("tkseal.kubeseal.KubeSeal.exists")
        mock_tk = mocker.patch("tkseal.tk.TK.exists")
        mock_kubectl = mocker.patch("tkseal.kubectl.KubeCtl.exists")

        mock_kubectl.return_value = True
        mock_tk.return_value = True
        mock_kubeseal.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ['ready'])
        assert result.exit_code == 0
        assert "✅ Kubectl is installed" in result.output
        assert "✅ tk is installed" in result.output
        assert "❌ Kubeseal is NOT installed" in result.output

        runner = CliRunner()
        result = runner.invoke(cli, ['ready'])
        assert result.exit_code == 0
