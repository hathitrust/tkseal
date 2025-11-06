"""Tests for configuration module."""

from tkseal import configuration


def test_configuration_constant():
    """Test configuration constants for plain and sealed secrets files.
    - Verify that PLAIN_SECRETS_FILE is "plain_secrets.json".
    - Verify that SEALED_SECRETS_FILE is "sealed_secrets.json".
    - Ensure both constants are strings.
    - Ensure both file names end with .json extension.
    """

    assert configuration.PLAIN_SECRETS_FILE == "plain_secrets"

    assert configuration.SEALED_SECRETS_FILE == "sealed_secrets"

    assert isinstance(configuration.PLAIN_SECRETS_FILE, str)
    assert isinstance(configuration.SEALED_SECRETS_FILE, str)
