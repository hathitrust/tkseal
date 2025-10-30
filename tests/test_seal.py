"""Tests for Seal class."""

import json
from pathlib import Path

import pytest

from tkseal.exceptions import TKSealError
from tkseal.seal import Seal


@pytest.fixture
def mock_kubeseal(mocker):
    """Mock KubeSeal.seal for tests."""
    mock = mocker.patch("tkseal.seal.KubeSeal.seal")
    mock.return_value = "sealed-value"
    return mock


@pytest.fixture
def seal_test_setup(simple_mock_secret_state, tmp_path, sample_plain_secrets):
    """Setup a common seal test environment with temp file and mock state."""

    sealed_file = tmp_path / "sealed_secrets.json"
    simple_mock_secret_state.sealed_secrets_file_path = sealed_file
    simple_mock_secret_state.plain_secrets.return_value = sample_plain_secrets
    return simple_mock_secret_state, sealed_file


class TestSealInitialization:
    """Test Seal class initialization."""

    def test_seal_initializes_with_secret_state(self, simple_mock_secret_state):
        """Test Seal can be initialized with SecretState."""
        seal = Seal(simple_mock_secret_state)

        assert seal.secret_state == simple_mock_secret_state


class TestSealKubesealMethod:
    """Test Seal.kubeseal() wrapper method."""

    def test_kubeseal_calls_wrapper_with_correct_params(
        self, mock_kubeseal, simple_mock_secret_state
    ):
        """Test kubeseal() passes context, namespace, name, value correctly."""
        seal = Seal(simple_mock_secret_state)
        result = seal.kubeseal(name="test-secret", value="plain-value")

        # Verify KubeSeal.seal was called with the correct parameters
        mock_kubeseal.assert_called_once_with(
            context="some-context",
            namespace="some-namespace",
            name="test-secret",
            value="plain-value",
        )
        # Verify the method returns the sealed value from KubeSeal.seal
        assert result == "sealed-value"


class TestSealRun:
    """Test Seal.run() method."""

    def test_run_seals_and_writes_secrets(self, mock_kubeseal, seal_test_setup):
        """Test run() seals all key-value pairs and writes proper SealedSecret JSON."""
        mock_state, sealed_file = seal_test_setup

        # Mock KubeSeal.seal to return different values for each key
        mock_kubeseal.side_effect = ["sealed-username", "sealed-password"]

        # Run seal
        seal = Seal(mock_state)
        seal.run()

        # Verify plain_secrets was called
        mock_state.plain_secrets.assert_called_once()

        # Verify KubeSeal.seal was called twice (once for each key)
        assert mock_kubeseal.call_count == 2

        # Verify calls were made with correct parameters
        calls = mock_kubeseal.call_args_list
        assert calls[0].kwargs["name"] == "app-secret"
        assert calls[0].kwargs["value"] == "admin"
        assert calls[1].kwargs["name"] == "app-secret"
        assert calls[1].kwargs["value"] == "secret123"

        # Verify file was written
        assert sealed_file.exists()
        content = sealed_file.read_text()

        # Verify it's pretty-printed JSON
        assert "\n" in content
        assert "  " in content  # 2-space indentation

        # Parse and verify structure
        sealed_secrets = json.loads(content)
        assert isinstance(sealed_secrets, list)
        assert len(sealed_secrets) == 1

        sealed_secret = sealed_secrets[0]
        assert sealed_secret["kind"] == "SealedSecret"
        assert sealed_secret["apiVersion"] == "bitnami.com/v1alpha1"
        assert sealed_secret["metadata"]["name"] == "app-secret"
        assert sealed_secret["metadata"]["namespace"] == "some-namespace"
        assert sealed_secret["spec"]["template"]["metadata"]["name"] == "app-secret"
        assert (
            sealed_secret["spec"]["template"]["metadata"]["namespace"]
            == "some-namespace"
        )
        assert "encryptedData" in sealed_secret["spec"]

        # Verify encrypted data contains sealed values
        encrypted_data = sealed_secret["spec"]["encryptedData"]
        assert encrypted_data["username"] == "sealed-username"
        assert encrypted_data["password"] == "sealed-password"

    def test_run_handles_multiple_secrets(
        self,
        mock_kubeseal,
        simple_mock_secret_state,
        sample_plain_secrets_multiple,
        tmp_path,
    ):
        """Test run() processes multiple secrets from plain_secrets.json."""
        # Setup
        sealed_file = tmp_path / "sealed_secrets.json"
        simple_mock_secret_state.sealed_secrets_file_path = sealed_file
        simple_mock_secret_state.plain_secrets.return_value = (
            sample_plain_secrets_multiple
        )

        # Run seal
        seal = Seal(simple_mock_secret_state)
        seal.run()

        # Verify two secrets were processed
        sealed_secrets = json.loads(sealed_file.read_text())
        assert len(sealed_secrets) == 2
        assert sealed_secrets[0]["metadata"]["name"] == "app-secret"
        assert sealed_secrets[1]["metadata"]["name"] == "db-secret"

        # Verify kubeseal was called 4 times (2 keys per secret)
        assert mock_kubeseal.call_count == 4

    def test_run_with_empty_plain_secrets(
        self, mock_kubeseal, simple_mock_secret_state, tmp_path
    ):
        """Test run() handles empty plain_secrets.json."""
        sealed_file = tmp_path / "sealed_secrets.json"
        simple_mock_secret_state.sealed_secrets_file_path = sealed_file

        # Run seal
        seal = Seal(simple_mock_secret_state)
        seal.run()

        # Verify the file was written with an empty array
        sealed_secrets = json.loads(sealed_file.read_text())
        assert sealed_secrets == []

        # Verify kubeseal was never called
        mock_kubeseal.assert_not_called()


class TestSealErrorHandling:
    """Test Seal error handling."""

    def test_run_propagates_kubeseal_error(self, mock_kubeseal, seal_test_setup):
        """Test run() propagates TKSealError from KubeSeal.seal()."""
        mock_state, _ = seal_test_setup

        # Mock KubeSeal.seal to raise TKSealError
        mock_kubeseal.side_effect = TKSealError("kubeseal command failed")

        # Run seal and expect error
        seal = Seal(mock_state)
        with pytest.raises(TKSealError) as exc_info:
            seal.run()

        assert "kubeseal command failed" in str(exc_info.value)

    def test_run_handles_invalid_json(self, simple_mock_secret_state):
        """Test run() handles malformed plain_secrets.json."""
        # Setup
        simple_mock_secret_state.plain_secrets.return_value = "invalid json {{"

        # Run seal and expect JSONDecodeError
        seal = Seal(simple_mock_secret_state)
        with pytest.raises(json.JSONDecodeError):
            seal.run()

    def test_run_handles_file_write_error(self, mocker, mock_kubeseal, seal_test_setup):
        """Test run() propagates file write errors."""
        mock_state, _ = seal_test_setup

        # Mock file write to raise error
        mock_write = mocker.patch.object(Path, "write_text")
        mock_write.side_effect = PermissionError("Permission denied")

        # Run seal and expect error
        seal = Seal(mock_state)
        with pytest.raises(PermissionError) as exc_info:
            seal.run()

        assert "Permission denied" in str(exc_info.value)
