import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from conftest import TEST_CONTEXT, TEST_NAMESPACE

from tkseal.exceptions import TKSealError
from tkseal.secret_state import PLAIN_SECRETS_FILE, SecretState


@pytest.fixture
def mock_tk_env():
    """Fixture for mocked TKEnvironment with standard test values"""
    with patch('tkseal.tk.TKEnvironment') as mock:
        instance = Mock()
        instance.context = TEST_CONTEXT
        instance.namespace = TEST_NAMESPACE
        mock.return_value = instance
        yield mock


class TestSecretState:
    def test_initialization(self, mock_tk_env, test_paths):
        """Test SecretState initialization with various path formats"""
        for path in test_paths:
            state = SecretState(path)
            
            normalized_path = str(Path(__file__).parent / "environments")
            print(f"Normalized Path: {normalized_path}")
            assert str(state._plain_secrets_file_path) == str(
                Path(normalized_path) / PLAIN_SECRETS_FILE)

    # def test_context_delegation(self, mock_tk_env):
    #     """Test context property delegates to TKEnvironment"""
    #     env_path = str(Path(__file__).parent / "environments")
    #     state = SecretState(env_path)
    #     assert state.context == TEST_CONTEXT

    # def test_namespace_delegation(self, mock_tk_env):
    #     """Test namespace property delegates to TKEnvironment"""
    #     env_path = str(Path(__file__).parent / "environments")
    #     state = SecretState(env_path)
    #     assert state.namespace == TEST_NAMESPACE

    # def test_plain_secrets_reading(self, mock_tk_env):
    #     """Test plain_secrets property reads file content"""
    #     env_path = str(Path(__file__).parent / "environments")
    #     state = SecretState(env_path)
    #     secrets = json.loads(state.plain_secrets)
    #     assert "test-secret" in secrets
    #     assert secrets["test-secret"]["username"] == "admin"
    #     assert secrets["test-secret"]["password"] == "secret123"

    # def test_plain_secrets_missing_file(self, mock_tk_env, tmp_path):
    #     """Test plain_secrets property returns empty string for missing file"""
    #     # Use tmp_path for a directory we know won't have the file
    #     state = SecretState(str(tmp_path))
    #     assert state.plain_secrets == ""

    # @patch('tkseal.secret.Secrets.for_tk_env')
    # def test_kube_secrets(self, mock_for_tk_env, mock_tk_env):
    #     """Test kube_secrets property retrieves cluster secrets"""
    #     test_secrets = {"cluster": "secret"}
    #     mock_secrets = Mock()
    #     mock_secrets.to_json.return_value = json.dumps(test_secrets)
    #     mock_for_tk_env.return_value = mock_secrets

    #     env_path = str(Path(__file__).parent / "environments")
    #     print(f"Env Path: {env_path}")
    #     print(f"Parent Path: {Path(__file__).parent}")
    #     state = SecretState(env_path)
    #     assert json.loads(state.kube_secrets) == test_secrets

    # @patch('tkseal.secret.Secrets.for_tk_env')
    # def test_kube_secrets_error(self, mock_for_tk_env, mock_tk_env):
    #     """Test kube_secrets property handles errors"""
    #     mock_for_tk_env.side_effect = Exception("Cluster error")

    #     env_path = str(Path(__file__).parent / "environments")
    #     state = SecretState(env_path)
    #     with pytest.raises(TKSealError) as exc_info:
    #         _ = state.kube_secrets
    #     assert "Failed to get secrets from cluster" in str(exc_info.value)
