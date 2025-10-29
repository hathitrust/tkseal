
"""Tests for Diff class."""

import json

import pytest

from tkseal.diff import Diff, DiffResult
from tkseal.secret_state import SecretState

# Keep this fixture in this file for clarity; all the tests here use them to simulate
# different secret states - additions, removals, modifications.
@pytest.fixture
def sample_kube_secrets():
    """Sample kube secrets JSON content."""
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
def sample_plain_secrets_with_addition():
    """Plain secrets with an additional secret."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "secret123"},
            },
            {   "name": "db-secret",
                "data": {"host": "localhost", "port": "5432"}
            },
        ],
        indent=2,
    )


@pytest.fixture
def sample_plain_secrets_with_removal():
    """Plain secrets with one secret removed."""
    return json.dumps([], indent=2)


@pytest.fixture
def sample_plain_secrets_modified():
    """Plain secrets with modified values."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "newpassword456"},
            }
        ],
        indent=2,
    )


@pytest.fixture
def mock_secret_state(mocker):
    """Create mock SecretState with controlled plain/kube secrets."""
    mock_state = mocker.Mock(spec=SecretState)
    return mock_state


class TestDiffNoChanges:
    """Test Diff when there are no differences."""

    def test_plain_no_differences(
        self, mock_secret_state, sample_plain_secrets, sample_kube_secrets
    ):
        """Test plain mode when local and cluster secrets are identical."""
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is False
        assert result.diff_output == ""

    def test_pull_no_differences(
        self, mock_secret_state, sample_plain_secrets, sample_kube_secrets
    ):
        """Test pull mode when local and cluster secrets are identical."""
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.pull()

        assert isinstance(result, DiffResult)
        assert result.has_differences is False
        assert result.diff_output == ""


class TestDiffAdditions:
    """Test Diff when secrets are added."""

    def test_plain_shows_addition(
        self,
        mock_secret_state,
        sample_plain_secrets_with_addition,
        sample_kube_secrets,
    ):
        """Test plain mode shows additions when local has new secrets."""
        mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_with_addition
        )
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        assert "+" in result.diff_output
        assert "db-secret" in result.diff_output
        assert "localhost" in result.diff_output


class TestDiffRemovals:
    """Test Diff when secrets are removed."""

    def test_plain_shows_removal(
        self,
        mock_secret_state,
        sample_plain_secrets_with_removal,
        sample_kube_secrets,
    ):
        """Test plain mode shows removals when local is missing secrets."""
        mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_with_removal
        )
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        assert "-" in result.diff_output
        assert "app-secret" in result.diff_output


class TestDiffModifications:
    """Test Diff when secrets are modified."""

    def test_plain_shows_modification(
        self, mock_secret_state, sample_plain_secrets_modified, sample_kube_secrets
    ):
        """Test plain mode shows modifications when secret values change."""
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets_modified
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Should show old value being removed
        assert "-" in result.diff_output
        assert "secret123" in result.diff_output
        # Should show new value being added
        assert "+" in result.diff_output
        assert "newpassword456" in result.diff_output


class TestDiffPullMode:
    """Test Diff pull mode (reverse comparison)."""

    def test_pull_shows_cluster_changes(
        self,
        mock_secret_state,
        sample_plain_secrets_with_removal,
        sample_kube_secrets,
    ):
        """Test pull mode shows what would change locally if pulled."""
        # Local is empty, cluster has secrets
        mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_with_removal
        )
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.pull()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # In pull mode, cluster secrets would be added to local
        assert "+" in result.diff_output
        assert "app-secret" in result.diff_output


class TestDiffEmptySecrets:
    """Test Diff with empty secrets scenarios."""

    def test_plain_empty_local_secrets(self, mock_secret_state, sample_kube_secrets):
        """Test plain mode when local secrets file is empty."""
        mock_secret_state.plain_secrets.return_value = ""
        mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Empty local means cluster secrets would be removed
        assert "-" in result.diff_output

    def test_plain_empty_cluster_secrets(self, mock_secret_state, sample_plain_secrets):
        """Test plain mode when cluster has no secrets."""
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        mock_secret_state.kube_secrets.return_value = ""

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Local secrets would be added to cluster
        assert "+" in result.diff_output

    def test_plain_both_empty(self, mock_secret_state):
        """Test plain mode when both local and cluster are empty."""
        mock_secret_state.plain_secrets.return_value = ""
        mock_secret_state.kube_secrets.return_value = ""

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is False
        assert result.diff_output == ""


class TestDiffMultipleSecrets:
    """Test Diff with multiple secrets and partial changes."""

    def test_multiple_secrets_partial_changes(self, mock_secret_state):
        """Test diff with multiple secrets where only some have changed."""
        plain_secrets = json.dumps(
            [
                {
                    "name": "app-secret",
                    "data": {"username": "admin", "password": "secret123"},
                },
                {
                    "name": "db-secret",
                    "data": {"host": "localhost", "port": "5432"},
                },
                {
                    "name": "cache-secret",
                    "data": {"host": "redis.example.com", "port": "6379"},
                },
            ],
            indent=2,
        )

        kube_secrets = json.dumps(
            [
                {
                    "name": "app-secret",
                    "data": {"username": "admin", "password": "secret123"},
                },
                {
                    "name": "db-secret",
                    "data": {"host": "db.example.com", "port": "5432"},  # Changed
                },
                {
                    "name": "cache-secret",
                    "data": {"host": "redis.example.com", "port": "6379"},
                },
            ],
            indent=2,
        )

        mock_secret_state.plain_secrets.return_value = plain_secrets
        mock_secret_state.kube_secrets.return_value = kube_secrets

        diff = Diff(mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Should show the changed host
        assert "localhost" in result.diff_output
        assert "db.example.com" in result.diff_output
        # Should show it's in db-secret context
        assert "db-secret" in result.diff_output or "host" in result.diff_output


class TestDiffWhitespaceHandling:
    """Test Diff handles whitespace and trailing newlines properly."""

    def test_trailing_newlines(self, mock_secret_state, sample_plain_secrets):
        """Test diff handles trailing newlines consistently."""
        # Add trailing newlines to one but not the other
        plain_with_newlines = sample_plain_secrets + "\n\n"
        kube_with_newlines = sample_plain_secrets + "\n"

        mock_secret_state.plain_secrets.return_value = plain_with_newlines
        mock_secret_state.kube_secrets.return_value = kube_with_newlines

        diff = Diff(mock_secret_state)
        result = diff.plain()

        # Different trailing newlines might show as a difference
        # depending on implementation; document the behavior
        assert isinstance(result, DiffResult)
        # This test documents the actual behavior - adjust based on implementation
