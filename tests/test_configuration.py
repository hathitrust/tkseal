"""Tests for configuration module."""

from tkseal import configuration


def test_plain_secrets_file_constant():
    """Test that PLAIN_SECRETS_FILE constant is defined correctly."""
    assert configuration.PLAIN_SECRETS_FILE == "plain_secrets.json"


def test_sealed_secrets_file_constant():
    """Test that SEALED_SECRETS_FILE constant is defined correctly."""
    assert configuration.SEALED_SECRETS_FILE == "sealed_secrets.json"


def test_constants_are_strings():
    """Test that configuration constants are strings."""
    assert isinstance(configuration.PLAIN_SECRETS_FILE, str)
    assert isinstance(configuration.SEALED_SECRETS_FILE, str)


def test_constants_have_json_extension():
    """Test that both configuration files have .json extension."""
    assert configuration.PLAIN_SECRETS_FILE.endswith(".json")
    assert configuration.SEALED_SECRETS_FILE.endswith(".json")
