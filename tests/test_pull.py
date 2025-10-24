"""Tests for Pull class."""

import json
from pathlib import Path

import pytest

from tkseal.diff import DiffResult
from tkseal.exceptions import TKSealError
from tkseal.pull import Pull
from tkseal.secret_state import SecretState


@pytest.fixture
def mock_secret_state(mocker):
    """Create mock SecretState with controlled behavior."""
    mock_state = mocker.Mock(spec=SecretState)
    mock_state.plain_secrets_file_path = Path("/fake/path/plain_secrets.json")
    return mock_state


@pytest.fixture
def sample_plain_secrets():
    """Sample plain_secrets.json content."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "secret123"},
            }
        ],
        indent=2,
    )


@pytest.fixture
def sample_kube_secrets():
    """Sample kube secrets JSON content."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "newsecret456"},
            }
        ],
        indent=2,
    )


class TestPullInitialization:
    """Test Pull class initialization."""

    def test_pull_initializes_with_secret_state(self, mock_secret_state):
        """Test Pull class can be initialized with a SecretState."""
        pull = Pull(mock_secret_state)

        assert pull.secret_state == mock_secret_state


class TestPullRun:
    """Test Pull.run() method."""

    def test_run_no_differences(self, mocker, mock_secret_state, sample_plain_secrets):
        """Test run() when plain and kube secrets are identical."""
        # Setup: Mock Diff to return no differences
        mock_diff = mocker.Mock()
        mock_diff.pull.return_value = DiffResult(has_differences=False, diff_output="")
        mocker.patch("tkseal.pull.Diff", return_value=mock_diff)

        pull = Pull(mock_secret_state)
        result = pull.run()

        # Should call Diff.pull()
        mock_diff.pull.assert_called_once()

        # Should return DiffResult with no differences
        assert isinstance(result, DiffResult)
        assert result.has_differences is False
        assert result.diff_output == ""

    def test_run_with_differences(
        self, mocker, mock_secret_state, sample_plain_secrets, sample_kube_secrets
    ):
        """Test run() when secrets differ."""
        # Setup: Mock Diff to return differences
        mock_diff = mocker.Mock()
        mock_diff.pull.return_value = DiffResult(
            has_differences=True, diff_output="-old\n+new"
        )
        mocker.patch("tkseal.pull.Diff", return_value=mock_diff)

        pull = Pull(mock_secret_state)
        result = pull.run()

        # Should call Diff.pull()
        mock_diff.pull.assert_called_once()

        # Should return DiffResult with differences
        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        assert "-old" in result.diff_output
        assert "+new" in result.diff_output

    def test_run_calls_diff_with_secret_state(self, mocker, mock_secret_state):
        """Test that run() creates Diff with the correct SecretState."""
        mock_diff_class = mocker.patch("tkseal.pull.Diff")
        mock_diff_instance = mocker.Mock()
        mock_diff_instance.pull.return_value = DiffResult(
            has_differences=False, diff_output=""
        )
        mock_diff_class.return_value = mock_diff_instance

        pull = Pull(mock_secret_state)
        pull.run()

        # Verify Diff was instantiated with the secret_state
        mock_diff_class.assert_called_once_with(mock_secret_state)


class TestPullWrite:
    """Test Pull.write() method."""

    def test_write_saves_kube_secrets_to_file(
        self, mocker, mock_secret_state, sample_kube_secrets
    ):
        """Test write() saves kube secrets to plain_secrets.json."""
        # Setup: Mock kube_secrets() to return test data
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        # Mock the file write operation
        mock_path = mocker.Mock(spec=Path)
        mock_secret_state.plain_secrets_file_path = mock_path

        pull = Pull(mock_secret_state)
        pull.write()

        # Should call kube_secrets()
        mock_secret_state.kube_secrets.assert_called_once()

        # Should write to the file
        mock_path.write_text.assert_called_once_with(sample_kube_secrets)

    def test_write_with_real_temp_file(
        self, mocker, tmp_path, mock_secret_state, sample_kube_secrets
    ):
        """Test write() actually writes to a real file."""
        # Setup: Create real temp file path
        temp_file = tmp_path / "plain_secrets.json"
        mock_secret_state.plain_secrets_file_path = temp_file
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        pull = Pull(mock_secret_state)
        pull.write()

        # Verify file was created
        assert temp_file.exists()

        # Verify file contents
        written_content = temp_file.read_text()
        assert written_content == sample_kube_secrets
        assert "app-secret" in written_content
        assert "newsecret456" in written_content

    def test_write_overwrites_existing_file(
        self, mocker, tmp_path, mock_secret_state, sample_kube_secrets
    ):
        """Test write() overwrites existing plain_secrets.json."""
        # Setup: Create file with old content
        temp_file = tmp_path / "plain_secrets.json"
        temp_file.write_text("old content")

        mock_secret_state.plain_secrets_file_path = temp_file
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        pull = Pull(mock_secret_state)
        pull.write()

        # Verify file was overwritten
        written_content = temp_file.read_text()
        assert written_content == sample_kube_secrets
        assert "old content" not in written_content


class TestPullErrorHandling:
    """Test Pull error handling."""

    def test_run_propagates_tkseal_error(self, mocker, mock_secret_state):
        """Test that run() propagates TKSealError from Diff."""
        # Setup: Mock Diff.pull() to raise TKSealError
        mock_diff = mocker.Mock()
        mock_diff.pull.side_effect = TKSealError("kubectl command failed")
        mocker.patch("tkseal.pull.Diff", return_value=mock_diff)

        pull = Pull(mock_secret_state)

        # Should propagate the exception
        with pytest.raises(TKSealError, match="kubectl command failed"):
            pull.run()

    def test_write_propagates_tkseal_error(self, mocker, mock_secret_state):
        """Test that write() propagates TKSealError from kube_secrets()."""
        # Setup: Mock kube_secrets() to raise TKSealError
        mock_secret_state.kube_secrets.side_effect = TKSealError(
            "Failed to retrieve cluster secrets"
        )

        pull = Pull(mock_secret_state)

        # Should propagate the exception
        with pytest.raises(TKSealError, match="Failed to retrieve cluster secrets"):
            pull.write()

    def test_write_propagates_file_write_error(self, mocker, mock_secret_state):
        """Test that write() propagates file write errors."""
        # Setup: Mock write_text to raise PermissionError
        mock_path = mocker.Mock(spec=Path)
        mock_path.write_text.side_effect = PermissionError("Permission denied")
        mock_secret_state.plain_secrets_file_path = mock_path
        mock_secret_state.kube_secrets.return_value = "test content"

        pull = Pull(mock_secret_state)

        # Should propagate the exception
        with pytest.raises(PermissionError, match="Permission denied"):
            pull.write()


class TestPullWorkflow:
    """Test complete Pull workflow."""

    def test_full_pull_workflow(
        self, mocker, tmp_path, sample_plain_secrets, sample_kube_secrets
    ):
        """Test complete workflow: run() shows diff, write() saves to file."""
        # Setup: Create a real SecretState-like mock
        mock_state = mocker.Mock(spec=SecretState)
        mock_state.plain_secrets_file_path = tmp_path / "plain_secrets.json"
        mock_state.plain_secrets.return_value = sample_plain_secrets
        mock_state.kube_secrets.return_value = sample_kube_secrets

        # Mock Diff to return differences
        mock_diff = mocker.Mock()
        mock_diff.pull.return_value = DiffResult(
            has_differences=True, diff_output="-secret123\n+newsecret456"
        )
        mocker.patch("tkseal.pull.Diff", return_value=mock_diff)

        # Step 1: Run to show differences
        pull = Pull(mock_state)
        result = pull.run()

        assert result.has_differences is True
        assert "secret123" in result.diff_output
        assert "newsecret456" in result.diff_output

        # Step 2: Write to save changes
        pull.write()

        # Verify file was written with kube secrets
        assert mock_state.plain_secrets_file_path.exists()
        written_content = mock_state.plain_secrets_file_path.read_text()
        assert written_content == sample_kube_secrets
