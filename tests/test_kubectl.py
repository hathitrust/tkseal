import pytest

from tkseal.exceptions import TKSealError
from tkseal.kubectl import KubeCtl


class TestKubectl:
    def test_kubectl_exists_returns_true_when_installed(self, mocker):
        """Return True when kubectl is on PATH.
        This test mocks shutil.which to simulate kubectl being installed.
        We patch shutil.which to test the implementation of KubeCtl.exists
        """

        mock_which = mocker.patch("tkseal.kubectl.shutil.which")
        mock_which.return_value = "/usr/local/bin/kubectl"

        assert KubeCtl.exists() is True
        mock_which.assert_called_once_with("kubectl")

    def test_kubectl_exists_false_when_not_installed(self, mocker):
        """Return False when kubectl is not on PATH."""

        mock_which = mocker.patch("tkseal.kubectl.shutil.which")
        mock_which.return_value = None

        assert KubeCtl.exists() is False

    def test_get_secrets_success(self, mocker, load_secret_file):
        test_secrets_yaml, test_secrets_dict = load_secret_file

        mock_run = mocker.patch("tkseal.kubectl.KubeCtl._run_command")
        #with patch('tkseal.kubectl.KubeCtl._run_command') as mock_run:
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

    def test_get_secrets_kubectl_error(self, mocker):
        mock_run = mocker.patch("tkseal.kubectl.KubeCtl._run_command")

        mock_run.side_effect = Exception("kubectl error")

        with pytest.raises(TKSealError) as exc_info:
            KubeCtl.get_secrets("test-context", "test-namespace")

        assert "Failed to get secrets" in str(exc_info.value)

    def test_get_secrets_invalid_yaml(self, mocker):

        mock_run = mocker.patch("tkseal.kubectl.KubeCtl._run_command")
        mock_run.return_value = "invalid: yaml: :"

        with pytest.raises(TKSealError) as exc_info:
            KubeCtl.get_secrets("test-context", "test-namespace")

        assert "Failed to parse secrets YAML" in str(exc_info.value)
