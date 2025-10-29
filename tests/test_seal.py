"""Tests for Seal class."""

import json
from pathlib import Path

import pytest

from tkseal.exceptions import TKSealError
from tkseal.seal import Seal
from tkseal.secret_state import SecretState


@pytest.fixture
def mock_secret_state(mocker):
    """Mock SecretState with controlled behavior."""
    mock_state = mocker.Mock(spec=SecretState)
    mock_state.context = "test-context"
    mock_state.namespace = "test-namespace"
    mock_state.plain_secrets_file_path = Path("/fake/plain_secrets.json")
    mock_state.sealed_secrets_file_path = Path("/fake/sealed_secrets.json")
    return mock_state

@pytest.fixture
def sample_plain_secrets_multiple():
    """Sample plain_secrets.json with multiple secrets."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "secret123"},
            },
            {
                "name": "db-secret",
                "data": {"db_host": "localhost", "db_password": "dbpass456"},
            },
        ]
    )


class TestSealInitialization:
    """Test Seal class initialization."""

    def test_seal_initializes_with_secret_state(self, mock_secret_state):
        """Test Seal can be initialized with SecretState."""
        seal = Seal(mock_secret_state)

        assert seal.secret_state == mock_secret_state


class TestSealKubesealMethod:
    """Test Seal.kubeseal() wrapper method."""

    def test_kubeseal_calls_wrapper_with_correct_params(
        self, mocker, mock_secret_state
    ):
        """Test kubeseal() passes context, namespace, name, value correctly."""
        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "sealed-value-xyz"

        seal = Seal(mock_secret_state)
        result = seal.kubeseal(name="test-secret", value="plain-value")

        # Verify KubeSeal.seal was called with the correct parameters
        mock_kubeseal.assert_called_once_with(
            context="test-context",
            namespace="test-namespace",
            name="test-secret",
            value="plain-value",
        )
        assert result == "sealed-value-xyz"

    def test_kubeseal_returns_sealed_value(self, mocker, mock_secret_state):
        """Test kubeseal() returns the sealed value from KubeSeal.seal()."""
        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "AgBZ8Xn+encrypted+base64=="

        seal = Seal(mock_secret_state)
        result = seal.kubeseal(name="app-secret", value="super-secret-password")

        assert result == "AgBZ8Xn+encrypted+base64=="


class TestSealRun:
    """Test Seal.run() method."""

    def test_run_reads_plain_secrets(self, mocker, mock_secret_state, sample_plain_secrets):
        """Test run() reads plain_secrets from secret_state."""
        # Mock plain_secrets() method
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets

        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "sealed-value"

        # Mock file write
        mock_write = mocker.patch.object(Path, "write_text")

        seal = Seal(mock_secret_state)
        seal.run()

        # Verify plain_secrets was called
        mock_secret_state.plain_secrets.assert_called_once()

    def test_run_creates_sealed_secret_structure(
        self, mocker, mock_secret_state, sample_plain_secrets, tmp_path
    ):
        """Test run() creates correct SealedSecret JSON structure."""
        # Setup
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        sealed_file = tmp_path / "sealed_secrets.json"
        mock_secret_state.sealed_secrets_file_path = sealed_file

        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "sealed-value-123"

        # Run seal
        seal = Seal(mock_secret_state)
        seal.run()

        # Verify file was written
        assert sealed_file.exists()

        # Parse and verify structure
        sealed_secrets = json.loads(sealed_file.read_text())
        assert len(sealed_secrets) == 1

        sealed_secret = sealed_secrets[0]
        assert sealed_secret["kind"] == "SealedSecret"
        assert sealed_secret["apiVersion"] == "bitnami.com/v1alpha1"
        assert sealed_secret["metadata"]["name"] == "app-secret"
        assert sealed_secret["metadata"]["namespace"] == "test-namespace"
        assert sealed_secret["spec"]["template"]["metadata"]["name"] == "app-secret"
        assert (
            sealed_secret["spec"]["template"]["metadata"]["namespace"]
            == "test-namespace"
        )
        assert "encryptedData" in sealed_secret["spec"]

    def test_run_seals_all_secret_data_pairs(
        self, mocker, mock_secret_state, sample_plain_secrets, tmp_path
    ):
        """Test run() encrypts each key-value pair in secret data."""
        # Setup
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        sealed_file = tmp_path / "sealed_secrets.json"
        mock_secret_state.sealed_secrets_file_path = sealed_file

        # Mock KubeSeal.seal to return different values
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.side_effect = ["sealed-username", "sealed-password"]

        # Run seal
        seal = Seal(mock_secret_state)
        seal.run()

        # Verify KubeSeal.seal was called twice (once for each key)
        assert mock_kubeseal.call_count == 2

        # Verify calls were made with correct values
        calls = mock_kubeseal.call_args_list
        assert calls[0].kwargs["name"] == "app-secret"
        assert calls[0].kwargs["value"] == "admin"
        assert calls[1].kwargs["name"] == "app-secret"
        assert calls[1].kwargs["value"] == "secret123"

        # Verify encrypted data
        sealed_secrets = json.loads(sealed_file.read_text())
        encrypted_data = sealed_secrets[0]["spec"]["encryptedData"]
        assert encrypted_data["username"] == "sealed-username"
        assert encrypted_data["password"] == "sealed-password"

    def test_run_handles_multiple_secrets(
        self, mocker, mock_secret_state, sample_plain_secrets_multiple, tmp_path
    ):
        """Test run() processes multiple secrets from plain_secrets.json."""
        # Setup
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets_multiple
        sealed_file = tmp_path / "sealed_secrets.json"
        mock_secret_state.sealed_secrets_file_path = sealed_file

        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "sealed-value"

        # Run seal
        seal = Seal(mock_secret_state)
        seal.run()

        # Verify two secrets were processed
        sealed_secrets = json.loads(sealed_file.read_text())
        assert len(sealed_secrets) == 2
        assert sealed_secrets[0]["metadata"]["name"] == "app-secret"
        assert sealed_secrets[1]["metadata"]["name"] == "db-secret"

        # Verify kubeseal was called 4 times (2 keys per secret)
        assert mock_kubeseal.call_count == 4

    def test_run_writes_to_sealed_secrets_file(
        self, mocker, mock_secret_state, sample_plain_secrets, tmp_path
    ):
        """Test run() writes pretty-printed JSON to sealed_secrets.json."""
        # Setup
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets
        sealed_file = tmp_path / "sealed_secrets.json"
        mock_secret_state.sealed_secrets_file_path = sealed_file

        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "sealed-value"

        # Run seal
        seal = Seal(mock_secret_state)
        seal.run()

        # Verify file exists and is valid JSON
        assert sealed_file.exists()
        content = sealed_file.read_text()

        # Verify it's pretty-printed (has newlines and indentation)
        assert "\n" in content
        assert "  " in content  # 2-space indentation

        # Verify valid JSON
        parsed = json.loads(content)
        assert isinstance(parsed, list)

    def test_run_with_empty_plain_secrets(
        self, mocker, mock_secret_state, tmp_path
    ):
        """Test run() handles empty plain_secrets.json."""
        # Setup
        mock_secret_state.plain_secrets.return_value = "[]"
        sealed_file = tmp_path / "sealed_secrets.json"
        mock_secret_state.sealed_secrets_file_path = sealed_file

        # Mock KubeSeal.seal (should not be called)
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")

        # Run seal
        seal = Seal(mock_secret_state)
        seal.run()

        # Verify file was written with empty array
        sealed_secrets = json.loads(sealed_file.read_text())
        assert sealed_secrets == []

        # Verify kubeseal was never called
        mock_kubeseal.assert_not_called()


class TestSealErrorHandling:
    """Test Seal error handling."""

    def test_run_propagates_kubeseal_error(self, mocker, mock_secret_state, sample_plain_secrets):
        """Test run() propagates TKSealError from KubeSeal.seal()."""
        # Setup
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets

        # Mock KubeSeal.seal to raise TKSealError
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.side_effect = TKSealError("kubeseal command failed")

        # Run seal and expect error
        seal = Seal(mock_secret_state)
        with pytest.raises(TKSealError) as exc_info:
            seal.run()

        assert "kubeseal command failed" in str(exc_info.value)

    def test_run_handles_invalid_json(self, mocker, mock_secret_state):
        """Test run() handles malformed plain_secrets.json."""
        # Setup
        mock_secret_state.plain_secrets.return_value = "invalid json {{"

        # Run seal and expect JSONDecodeError
        seal = Seal(mock_secret_state)
        with pytest.raises(json.JSONDecodeError):
            seal.run()

    def test_run_handles_file_write_error(
        self, mocker, mock_secret_state, sample_plain_secrets
    ):
        """Test run() propagates file write errors."""
        # Setup
        mock_secret_state.plain_secrets.return_value = sample_plain_secrets

        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.return_value = "sealed-value"

        # Mock file write to raise error
        mock_write = mocker.patch.object(Path, "write_text")
        mock_write.side_effect = PermissionError("Permission denied")

        # Run seal and expect error
        seal = Seal(mock_secret_state)
        with pytest.raises(PermissionError) as exc_info:
            seal.run()

        assert "Permission denied" in str(exc_info.value)


class TestSealWorkflow:
    """Test complete Seal workflow."""

    def test_full_seal_workflow(self, mocker, tmp_path):
        """Test complete workflow: read plain, seal each value, write sealed."""
        # Setup real temp files
        plain_file = tmp_path / "plain_secrets.json"
        sealed_file = tmp_path / "sealed_secrets.json"

        # Write plain secrets
        plain_secrets = [
            {
                "name": "test-secret",
                "data": {"KEY1": "value1", "KEY2": "value2"},
            }
        ]
        plain_file.write_text(json.dumps(plain_secrets))

        # Create mock SecretState
        mock_state = mocker.Mock(spec=SecretState)
        mock_state.context = "prod-context"
        mock_state.namespace = "prod-namespace"
        mock_state.plain_secrets_file_path = plain_file
        mock_state.sealed_secrets_file_path = sealed_file
        mock_state.plain_secrets.return_value = plain_file.read_text()

        # Mock KubeSeal.seal
        mock_kubeseal = mocker.patch("tkseal.seal.KubeSeal.seal")
        mock_kubeseal.side_effect = ["sealed-key1", "sealed-key2"]

        # Run seal
        seal = Seal(mock_state)
        seal.run()

        # Verify sealed file was created
        assert sealed_file.exists()

        # Verify sealed secrets structure
        sealed_secrets = json.loads(sealed_file.read_text())
        assert len(sealed_secrets) == 1
        assert sealed_secrets[0]["kind"] == "SealedSecret"
        assert sealed_secrets[0]["metadata"]["name"] == "test-secret"
        assert sealed_secrets[0]["metadata"]["namespace"] == "prod-namespace"
        assert sealed_secrets[0]["spec"]["encryptedData"]["KEY1"] == "sealed-key1"
        assert sealed_secrets[0]["spec"]["encryptedData"]["KEY2"] == "sealed-key2"

        # Verify kubeseal was called with correct parameters
        assert mock_kubeseal.call_count == 2
        calls = mock_kubeseal.call_args_list
        assert calls[0].kwargs["context"] == "prod-context"
        assert calls[0].kwargs["namespace"] == "prod-namespace"
        assert calls[0].kwargs["name"] == "test-secret"
        assert calls[0].kwargs["value"] == "value1"