from unittest.mock import patch

import pytest

from tkseal.exceptions import TKSealError
from tkseal.kubectl import KubeCtl


class TestKubectl:
    @patch("tkseal.kubectl.shutil.which", return_value="/usr/local/bin/kubectl")
    def test_kubectl_exists_returns_true_when_installed(self, mock_which):
        """Return True when kubectl is on PATH.
        This test mocks shutil.which to simulate kubectl being installed.
        """
        assert KubeCtl.exists() is True
        mock_which.assert_called_once_with("kubectl")

    @patch("tkseal.kubectl.shutil.which", return_value=None)
    def test_kubectl_exists_false_when_not_installed(self, _):
        """Return False when kubectl is not on PATH."""
        assert KubeCtl.exists() is False

    def test_get_secrets_success(self, load_secret_file):
        test_secrets_yaml, test_secrets_dict = load_secret_file
        with patch('tkseal.kubectl.KubeCtl._run_command') as mock_run:
            mock_run.return_value = test_secrets_yaml
            result = KubeCtl.get_secrets("test-context", "test-namespace")

            mock_run.assert_called_once_with(
                ["kubectl", "--context=test-context",
                    "--namespace=test-namespace", "get", "secrets", "-o", "yaml"]
            )
            assert result == test_secrets_dict
            # Verify structure of returned data
            assert result['apiVersion'] == 'v1'
            assert result['kind'] == 'List'
            assert 'items' in result
            assert len(result['items']) == 2

    def test_get_secrets_kubectl_error(self):
        with patch('tkseal.kubectl.KubeCtl._run_command') as mock_run:
            mock_run.side_effect = Exception("kubectl error")

            with pytest.raises(TKSealError) as exc_info:
                KubeCtl.get_secrets("test-context", "test-namespace")

            assert "Failed to get secrets" in str(exc_info.value)

    def test_get_secrets_invalid_yaml(self):
        with patch('tkseal.kubectl.KubeCtl._run_command') as mock_run:
            mock_run.return_value = "invalid: yaml: :"

            with pytest.raises(TKSealError) as exc_info:
                KubeCtl.get_secrets("test-context", "test-namespace")

            assert "Failed to parse secrets YAML" in str(exc_info.value)
