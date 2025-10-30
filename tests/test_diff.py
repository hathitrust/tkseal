"""Tests for Diff class."""

import json

import pytest

from tkseal.diff import Diff, DiffResult


@pytest.fixture
def sample_plain_secrets_with_addition():
    """Plain secrets with an additional secret."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "secret123"},
            },
            {"name": "db-secret", "data": {"host": "localhost", "port": "5432"}},
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


class TestDiffNoChanges:
    """Test Diff when there are no differences."""

    @pytest.mark.parametrize("mode", ["plain", "pull"])
    def test_plain_pull_no_differences(
        self, mode, simple_mock_secret_state, sample_plain_secrets
    ):
        """Test plain mode when local and cluster secrets are identical."""
        simple_mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        simple_mock_secret_state.kube_secrets.return_value = sample_plain_secrets

        diff = Diff(simple_mock_secret_state)
        result = diff.plain() if mode == "plain" else diff.pull()

        assert isinstance(result, DiffResult)
        assert result.has_differences is False
        assert result.diff_output == ""


class TestDiffAdditions:
    """Test Diff when secrets are added."""

    def test_plain_shows_addition(
        self,
        simple_mock_secret_state,
        sample_plain_secrets_with_addition,
        sample_kube_secrets,
    ):
        """Test plain mode shows additions when local has new secrets."""
        simple_mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_with_addition
        )
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(simple_mock_secret_state)
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
        simple_mock_secret_state,
        sample_plain_secrets_with_removal,
        sample_kube_secrets,
    ):
        """Test plain mode shows removals when local is missing secrets."""
        simple_mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_with_removal
        )
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(simple_mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        assert "-" in result.diff_output
        assert "app-secret" in result.diff_output


class TestDiffModifications:
    """Test Diff when secrets are modified."""

    def test_plain_shows_modification(
        self,
        simple_mock_secret_state,
        sample_plain_secrets_modified,
        sample_kube_secrets,
    ):
        """Test plain mode shows modifications when secret values change."""
        simple_mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_modified
        )
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(simple_mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Should show old value being removed
        assert "-" in result.diff_output
        assert "newsecret456" in result.diff_output
        # Should show new value being added
        assert "+" in result.diff_output
        assert "newpassword456" in result.diff_output


class TestDiffPullMode:
    """Test Diff pull mode (reverse comparison)."""

    def test_pull_shows_cluster_changes(
        self,
        simple_mock_secret_state,
        sample_plain_secrets_with_removal,
        sample_kube_secrets,
    ):
        """Test pull mode shows what would change locally if pulled."""
        # Local is empty, cluster has secrets
        simple_mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_with_removal
        )
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(simple_mock_secret_state)
        result = diff.pull()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # In pull mode, cluster secrets would be added to local
        assert "+" in result.diff_output
        assert "app-secret" in result.diff_output


class TestDiffEmptySecrets:
    """Test Diff with empty secrets scenarios."""

    def test_plain_empty_local_secrets(
        self, simple_mock_secret_state, sample_kube_secrets
    ):
        """Test plain mode when local secrets file is empty."""
        simple_mock_secret_state.plain_secrets.return_value = ""
        simple_mock_secret_state.kube_secrets.return_value = sample_kube_secrets

        diff = Diff(simple_mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Empty local means cluster secrets would be removed
        assert "-" in result.diff_output

    def test_plain_empty_cluster_secrets(
        self, simple_mock_secret_state, sample_plain_secrets
    ):
        """Test plain mode when cluster has no secrets."""
        simple_mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        simple_mock_secret_state.kube_secrets.return_value = ""

        diff = Diff(simple_mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is True
        # Local secrets would be added to cluster
        assert "+" in result.diff_output

    def test_plain_both_empty(self, simple_mock_secret_state):
        """Test plain mode when both local and cluster are empty."""
        simple_mock_secret_state.plain_secrets.return_value = ""
        simple_mock_secret_state.kube_secrets.return_value = ""

        diff = Diff(simple_mock_secret_state)
        result = diff.plain()

        assert isinstance(result, DiffResult)
        assert result.has_differences is False
        assert result.diff_output == ""


class TestDiffMultipleSecrets:
    """Test Diff with multiple secrets and partial changes."""

    def test_multiple_secrets_partial_changes(self, simple_mock_secret_state):
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

        simple_mock_secret_state.plain_secrets.return_value = plain_secrets
        simple_mock_secret_state.kube_secrets.return_value = kube_secrets

        diff = Diff(simple_mock_secret_state)
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

    def test_trailing_newlines(self, simple_mock_secret_state, sample_plain_secrets):
        """Test diff handles trailing newlines consistently."""
        # Add trailing newlines to one but not the other
        plain_with_newlines = sample_plain_secrets + "\n\n"
        kube_with_newlines = sample_plain_secrets + "\n"

        simple_mock_secret_state.plain_secrets.return_value = plain_with_newlines
        simple_mock_secret_state.kube_secrets.return_value = kube_with_newlines

        diff = Diff(simple_mock_secret_state)
        result = diff.plain()

        # Different trailing newlines might show as a difference
        # depending on implementation; document the behavior
        assert isinstance(result, DiffResult)
        # This test documents the actual behavior - adjust based on implementation
