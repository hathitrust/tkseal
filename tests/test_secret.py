import base64
from dataclasses import dataclass

import pytest

from tkseal.secret import Secret, SecretDataPair, Secrets


def test_secret_data_pair():
    pair = SecretDataPair(
        key="username",
        plain_value="admin",
        encoded_value=base64.b64encode("admin".encode()).decode()
    )
    assert pair.key == "username"
    assert pair.plain_value == "admin"
    assert pair.encoded_value == "YWRtaW4="


def test_secret_name():
    raw = {
        "metadata": {
            "name": "test-secret"
        },
        "data": {}
    }
    secret = Secret(raw)
    assert secret.name == "test-secret"


def test_secret_data():
    raw = {
        "metadata": {
            "name": "test-secret"
        },
        "data": {
            "username": "YWRtaW4=",  # base64 encoded "admin"
            "password": "c2VjcmV0"   # base64 encoded "secret"
        }
    }
    secret = Secret(raw)
    data = secret.data

    assert len(data) == 2
    assert isinstance(data[0], SecretDataPair)
    assert data[0].key == "username"
    assert data[0].plain_value == "admin"
    assert data[0].encoded_value == "YWRtaW4="

    assert data[1].key == "password"
    assert data[1].plain_value == "secret"
    assert data[1].encoded_value == "c2VjcmV0"


def test_secrets_collection():
    raw_secrets = [
        {
            "metadata": {"name": "secret1"},
            "data": {"key1": "dmFsdWUx"}  # base64 encoded "value1"
        },
        {
            "metadata": {"name": "secret2"},
            "data": {"key2": "dmFsdWUy"}  # base64 encoded "value2"
        }
    ]

    secrets = Secrets(raw_secrets)
    assert len(secrets.items) == 2
    assert all(isinstance(s, Secret) for s in secrets.items)
    assert [s.name for s in secrets.items] == ["secret1", "secret2"]

def test_secrets_data_collection():
    raw = {
        "metadata": {"name": "test-secret"},
        "data": {
            "user1": "dXNlcjE=",  # base64 encoded "user1"
            "user2": "dXNlcjI=",  # base64 encoded "user2"
            "user3": "dXNlcjM=",  # base64 encoded "user3"
            "user4": "dXNlcjQ=",  # base64 encoded "user4"
        },
    }
    secret = Secret(raw)
    data = secret.data

    assert len(data) == 4
    assert isinstance(data[0], SecretDataPair)
    assert data[0].key == "user1"
    assert data[0].plain_value == "user1"
    assert data[0].encoded_value == "dXNlcjE="

    assert data[1].key == "user2"
    assert data[1].plain_value == "user2"
    assert data[1].encoded_value == "dXNlcjI="
