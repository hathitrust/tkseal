import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Common test constants
TEST_CONTEXT = "test-context"
TEST_NAMESPACE = "test-namespace"
TEST_ENV_PATH = str(Path(__file__).parent / "environments")


@pytest.fixture
def load_secret_file():
    """Load the test secrets yaml file and return both raw yaml and parsed dict."""
    with open(os.path.join(os.path.dirname(__file__), 'secrets.yaml'), 'r') as f:
        test_secrets_yaml = f.read()
        test_secrets_dict = yaml.safe_load(test_secrets_yaml)
    return test_secrets_yaml, test_secrets_dict


@pytest.fixture
def mock_tk_env():
    """Shared fixture for mocked TKEnvironment"""
    with patch('tkseal.tk.TKEnvironment') as mock:
        instance = Mock()
        instance.context = TEST_CONTEXT
        instance.namespace = TEST_NAMESPACE
        mock.return_value = instance
        yield mock


@pytest.fixture
def test_paths():
    """Common test paths for normalization tests"""
    base = TEST_ENV_PATH
    return [
        base,
        f"{base}/",
        f"{base}.jsonnet",
        f"{base}.jsonnet/"
    ]


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    """Setup test environment directory structure"""
    env_path = Path(TEST_ENV_PATH)
    env_path.mkdir(exist_ok=True)

    # Define test data
    plain_secrets = {
        "test-secret": {
            "username": "admin",
            "password": "secret123"
        }
    }
    sealed_secrets = {
        "test-secret": {
            "username": "encrypted-admin-value",
            "password": "encrypted-password-value"
        }
    }

    # Write test data to files
    (env_path / "plain_secrets.json").write_text(json.dumps(plain_secrets, indent=4))
    (env_path / "sealed_secrets.json").write_text(json.dumps(sealed_secrets, indent=4))

    yield

    # Cleanup test environment
    # if env_path.exists():
    #     for f in env_path.glob("*"):
    #         f.unlink()
    #     env_path.rmdir()
