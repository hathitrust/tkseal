import os

import pytest
import yaml
import json


@pytest.fixture
def load_secret_file():
    """Load the test secrets yaml file and return both raw yaml and parsed dict."""
    with open(os.path.join(os.path.dirname(__file__), "secrets.yaml")) as f:
        test_secrets_yaml = f.read()
        test_secrets_dict = yaml.safe_load(test_secrets_yaml)
    return test_secrets_yaml, test_secrets_dict

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
