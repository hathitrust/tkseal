"""Tests for Pull class."""

from pathlib import Path

import pytest

from tkseal.exceptions import TKSealError
from tkseal.pull import Pull


class TestPullInitialization:
    """Test Pull class initialization."""

    def test_pull_initializes_with_secret_state(self, simple_mock_secret_state):
        """Test Pull class can be initialized with a SecretState."""
        pull = Pull(simple_mock_secret_state)

        assert pull.secret_state == simple_mock_secret_state


class TestPullWrite:
    """Test Pull.write() method."""

    def test_write_saves_kube_secrets_to_file(
        self, mocker, simple_mock_secret_state, sample_kube_secrets
    ):
        """Test write() saves kube secrets to plain_secrets.json."""
        # Setup: Mock kube_secrets() to return test data
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        # Mock the file write operation
        mock_path = mocker.Mock(spec=Path)
        simple_mock_secret_state.plain_secrets_file_path = mock_path

        pull = Pull(simple_mock_secret_state)
        pull.write()

        # Should call kube_secrets()
        simple_mock_secret_state.kube_secrets.assert_called_once()

        # Should write to the file
        mock_path.write_text.assert_called_once_with(sample_kube_secrets)

    def test_write_with_real_temp_file(
        self, tmp_path, simple_mock_secret_state, sample_kube_secrets
    ):
        """Test write() actually writes to a real file."""
        # Setup: Create real temp file path
        temp_file = tmp_path / "plain_secrets.json"
        simple_mock_secret_state.plain_secrets_file_path = temp_file
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        pull = Pull(simple_mock_secret_state)
        pull.write()

        # Verify file was created
        assert temp_file.exists()

        # Verify file contents
        written_content = temp_file.read_text()
        assert written_content == sample_kube_secrets
        assert "app-secret" in written_content
        assert "newsecret456" in written_content

    def test_write_overwrites_existing_file(
        self, tmp_path, simple_mock_secret_state, sample_kube_secrets
    ):
        """Test write() overwrites existing plain_secrets.json."""
        # Setup: Create file with old content
        temp_file = tmp_path / "plain_secrets.json"
        temp_file.write_text("old content")

        simple_mock_secret_state.plain_secrets_file_path = temp_file
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        pull = Pull(simple_mock_secret_state)
        pull.write()

        # Verify file was overwritten
        written_content = temp_file.read_text()
        assert written_content == sample_kube_secrets
        assert "old content" not in written_content


class TestPullErrorHandling:
    """Test Pull error handling."""

    def test_run_propagates_tkseal_error(self, mocker, simple_mock_secret_state):
        """Test that run() propagates TKSealError from Diff."""
        # Setup: Mock Diff.pull() to raise TKSealError
        mock_diff = mocker.Mock()
        mock_diff.pull.side_effect = TKSealError("kubectl command failed")
        mocker.patch("tkseal.pull.Diff", return_value=mock_diff)

        pull = Pull(simple_mock_secret_state)

        # Should propagate the exception
        with pytest.raises(TKSealError, match="kubectl command failed"):
            pull.run()

    def test_write_propagates_tkseal_error(self, simple_mock_secret_state):
        """Test that write() propagates TKSealError from kube_secrets()."""
        # Setup: Mock kube_secrets() to raise TKSealError
        simple_mock_secret_state.kube_secrets.side_effect = TKSealError(
            "Failed to retrieve cluster secrets"
        )

        pull = Pull(simple_mock_secret_state)

        # Should propagate the exception
        with pytest.raises(TKSealError, match="Failed to retrieve cluster secrets"):
            pull.write()

    def test_write_propagates_file_write_error(self, mocker, simple_mock_secret_state):
        """Test that write() propagates file write errors."""
        # Setup: Mock write_text to raise PermissionError
        mock_path = mocker.Mock(spec=Path)
        mock_path.write_text.side_effect = PermissionError("Permission denied")
        simple_mock_secret_state.plain_secrets_file_path = mock_path
        simple_mock_secret_state.kube_secrets.return_value = "test content"

        pull = Pull(simple_mock_secret_state)

        # Should propagate the exception
        with pytest.raises(PermissionError, match="Permission denied"):
            pull.write()


class TestPullWorkflow:
    """Test complete Pull workflow."""

    def test_full_pull_workflow(
        self, mocker, mock_secret_state, sample_plain_secrets, sample_kube_secrets
    ):
        """Test complete workflow: run() shows diff, write() saves it to file."""
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        # Step 1: Run to show differences
        pull = Pull(mock_secret_state)
        result = pull.run()

        # Step 2: Write to save changes
        pull.write()

        # Verify if the file was written with kube secrets
        assert mock_secret_state.plain_secrets_file_path.exists()
        written_content = mock_secret_state.plain_secrets_file_path.read_text()
        assert written_content == sample_kube_secrets

        assert result.has_differences is True
        assert "secret123" in result.diff_output
        assert "newsecret456" in result.diff_output
