import os
import yaml
import pytest


@pytest.fixture
def load_secret_file():
    """Load the test secrets yaml file and return both raw yaml and parsed dict."""
    with open(os.path.join(os.path.dirname(__file__), 'secrets.yaml'), 'r') as f:
        test_secrets_yaml = f.read()
        test_secrets_dict = yaml.safe_load(test_secrets_yaml)
    return test_secrets_yaml, test_secrets_dict