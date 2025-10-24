"""Tests for SecretState class."""

import json
import pytest

from pathlib import Path
from unittest.mock import Mock

from tkseal.secret_state import SecretState
from tkseal.tk import TKEnvironment
from tkseal.secret_state import normalize_tk_env_path


@pytest.fixture
def mock_tk_env(mocker):
    """Create a mock TKEnvironment."""
    mock_env = mocker.Mock(spec=TKEnvironment)
    mock_env.context = "test-context"
    mock_env.namespace = "test-namespace"
    return mock_env


@pytest.fixture
def temp_tanka_env(tmp_path):
    """Create a temporary Tanka environment directory structure."""
    env_path = tmp_path / "environments" / "test-env"
    env_path.mkdir(parents=True)

    # Create a sample plain_secrets.json
    plain_secrets = [
        {"name": "test-secret", "data": {"username": "admin", "password": "secret123"}}
    ]
    (env_path / "plain_secrets.json").write_text(json.dumps(plain_secrets, indent=2))

    return env_path


class TestSecretStateInitialization:
    """Test SecretState initialization and path handling."""

    def test_from_path_basic(self, mocker, temp_tanka_env, mock_tk_env):
        """Test basic initialization from a path."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        state = SecretState.from_path(str(temp_tanka_env))

        assert state.tk_env_path == str(temp_tanka_env)
        assert state.plain_secrets_file_path == temp_tanka_env / "plain_secrets.json"
        assert state.sealed_secrets_file_path == temp_tanka_env / "sealed_secrets.json"

    def test_from_path_with_trailing_slash(self, mocker, temp_tanka_env, mock_tk_env):
        """Test path normalization removes trailing slash."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        path_with_slash = str(temp_tanka_env) + "/"
        state = SecretState.from_path(path_with_slash)

        # Should normalize by removing trailing slash
        assert state.tk_env_path == str(temp_tanka_env)
        assert not state.tk_env_path.endswith("/")

    def test_from_path_with_jsonnet_extension(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test path normalization removes .jsonnet extension."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        path_with_jsonnet = str(temp_tanka_env) + "/main.jsonnet"
        state = SecretState.from_path(path_with_jsonnet)

        # Should normalize by removing /main.jsonnet
        assert state.tk_env_path == str(temp_tanka_env)
        assert not state.tk_env_path.endswith(".jsonnet")

    def test_from_path_with_trailing_slash_and_jsonnet(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test path normalization handles both trailing slash and .jsonnet."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        # Ruby regex: /\/(\w+.jsonnet)?$/ matches trailing slash with optional .jsonnet file
        path_complex = str(temp_tanka_env) + "/environment.jsonnet"
        state = SecretState.from_path(path_complex)

        assert state.tk_env_path == str(temp_tanka_env)

    def test_normalize_tk_env_path_function(self):
        """Test the normalize_tk_env_path function directly."""

        assert (
            normalize_tk_env_path("/path/to/env/") == "/path/to/env"
        )  # Trailing slash removed
        assert (
            normalize_tk_env_path("/path/to/env/main.jsonnet") == "/path/to/env"
        )  # .jsonnet removed
        assert (
            normalize_tk_env_path("/path/to/env") == "/path/to/env"
        )  # No change
        assert (
            normalize_tk_env_path("/path/to/env.jsonnet") == "/path/to"
        )

    def test_file_paths_use_configuration_constants(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test that file paths use configuration constants."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        state = SecretState.from_path(str(temp_tanka_env))

        # Verify paths end with configuration file names
        assert state.plain_secrets_file_path.name == "plain_secrets.json"
        assert state.sealed_secrets_file_path.name == "sealed_secrets.json"


class TestSecretStateProperties:
    """Test SecretState properties that delegate to TKEnvironment."""

    def test_context_property(self, mocker, temp_tanka_env, mock_tk_env):
        """Test that context property delegates to TKEnvironment."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        state = SecretState.from_path(str(temp_tanka_env))

        assert state.context == "test-context"

    def test_namespace_property(self, mocker, temp_tanka_env, mock_tk_env):
        """Test that namespace property delegates to TKEnvironment."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        state = SecretState.from_path(str(temp_tanka_env))

        assert state.namespace == "test-namespace"


class TestSecretStatePlainSecrets:
    """Test plain_secrets method for reading local files."""

    def test_plain_secrets_reads_existing_file(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test reading plain_secrets.json when it exists."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        state = SecretState.from_path(str(temp_tanka_env))
        content = state.plain_secrets()

        # Should read the file content
        assert content != ""
        assert "test-secret" in content
        assert "admin" in content

    def test_plain_secrets_returns_empty_string_when_file_missing(
        self, mocker, tmp_path, mock_tk_env
    ):
        """Test that plain_secrets returns empty string when file doesn't exist."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        # Create env directory without plain_secrets.json
        env_path = tmp_path / "empty-env"
        env_path.mkdir(parents=True)

        state = SecretState.from_path(str(env_path))
        content = state.plain_secrets()

        # Should return empty string, not raise exception
        assert content == ""

    def test_plain_secrets_returns_empty_string_on_read_error(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test that plain_secrets returns empty string on any read error."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        state = SecretState.from_path(str(temp_tanka_env))

        # Mock Path.read_text to raise an error
        mocker.patch.object(Path, "read_text", side_effect=PermissionError("No access"))

        content = state.plain_secrets()

        # Should handle error gracefully and return empty string
        assert content == ""


class TestSecretStateKubeSecrets:
    """Test kube_secrets method for retrieving cluster secrets."""

    def test_kube_secrets_calls_secrets_for_tk_env(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test that kube_secrets calls Secrets.for_tk_env with correct path."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        # Mock Secrets.for_tk_env
        mock_secrets = mocker.patch("tkseal.secret_state.Secrets")
        mock_secrets_instance = Mock()
        mock_secrets_instance.to_json.return_value = '{"test": "data"}'
        mock_secrets.for_tk_env.return_value = mock_secrets_instance

        state = SecretState.from_path(str(temp_tanka_env))
        result = state.kube_secrets()

        # Should call Secrets.for_tk_env with the normalized path
        mock_secrets.for_tk_env.assert_called_once_with(str(temp_tanka_env))
        assert result == '{"test": "data"}'

    def test_kube_secrets_uses_normalized_path(
        self, mocker, temp_tanka_env, mock_tk_env
    ):
        """Test that kube_secrets uses the normalized path."""
        mocker.patch("tkseal.secret_state.TKEnvironment", return_value=mock_tk_env)

        # Mock Secrets.for_tk_env
        mock_secrets = mocker.patch("tkseal.secret_state.Secrets")
        mock_secrets_instance = Mock()
        mock_secrets_instance.to_json.return_value = "{}"
        mock_secrets.for_tk_env.return_value = mock_secrets_instance

        # Pass path with trailing slash and .jsonnet
        path_with_extras = str(temp_tanka_env) + "/main.jsonnet"
        state = SecretState.from_path(path_with_extras)
        state.kube_secrets()

        # Should use normalized path (without trailing slash or .jsonnet)
        mock_secrets.for_tk_env.assert_called_once_with(str(temp_tanka_env))
