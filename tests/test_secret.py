import base64

from tkseal.secret import Secret, SecretDataPair, Secrets


def test_secret_data_pair():
    pair = SecretDataPair(
        key="username",
        plain_value="admin",
        encoded_value=base64.b64encode(b"admin").decode(),
    )
    assert pair.key == "username"
    assert pair.plain_value == "admin"
    assert pair.encoded_value == "YWRtaW4="


def test_secret_name():
    raw = {"metadata": {"name": "test-secret"}, "data": {}}
    secret = Secret(raw)
    assert secret.name == "test-secret"


def test_secret_data():
    raw = {
        "metadata": {"name": "test-secret"},
        "data": {
            "username": "YWRtaW4=",  # base64 encoded "admin"
            "password": "c2VjcmV0",  # base64 encoded "secret"
        },
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


def test_secret_empty_data():
    """Test that Secret handles missing data field gracefully."""
    raw = {"metadata": {"name": "empty-secret"}}  # No "data" key
    secret = Secret(raw)
    assert secret.name == "empty-secret"
    assert secret.data == []

def test_secrets_data_collection():
    """Test that Secret.data returns a list of SecretDataPair objects."""
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


def test_secrets_with_kubectl_format():
    """Test that Secrets accepts kubectl output format with 'items' key."""
    kubectl_output = {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {
                "metadata": {"name": "secret1"},
                "data": {"key1": "dmFsdWUx"},  # base64 encoded "value1"
            },
            {
                "metadata": {"name": "secret2"},
                "data": {"key2": "dmFsdWUy"},  # base64 encoded "value2"
            },
        ],
    }
    secrets = Secrets(kubectl_output)
    assert len(secrets.items) == 2
    assert secrets.items[0].name == "secret1"
    assert secrets.items[1].name == "secret2"

def test_secrets_for_tk_env(mocker):
    """Test that Secrets.for_tk_env() integrates TKEnvironment and KubeCtl correctly."""
    # Mock TKEnvironment
    mock_env = mocker.Mock()
    mock_env.context = "test-context"
    mock_env.namespace = "test-namespace"
    mock_tk_class = mocker.patch("tkseal.secret.TKEnvironment", return_value=mock_env)

    # Mock KubeCtl.get_secrets to return a kubectl format
    mock_kubectl_response = {
        "items": [{"metadata": {"name": "secret1"}, "data": {"key1": "dmFsdWUx"}}]
    }
    mock_kubectl = mocker.patch(
        "tkseal.secret.KubeCtl.get_secrets", return_value=mock_kubectl_response
    )

    # Call for_tk_env
    secrets = Secrets.for_tk_env("some/path")

    # Verify TKEnvironment was created with correct path
    mock_tk_class.assert_called_once_with("some/path")

    # Verify KubeCtl.get_secrets was called with correct context and namespace
    mock_kubectl.assert_called_once_with(
        context="test-context", namespace="test-namespace"
    )

    # Verify Secrets object was created correctly
    assert len(secrets.items) == 1
    assert secrets.items[0].name == "secret1"
