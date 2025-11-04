import pytest
from tkseal.exceptions import TKSealError
from tkseal.kubectl import KubeCtl

def test_get_secrets_kubectl_error(mocker):
    mock_run = mocker.patch("tkseal.tkseal_utils.run_command")

    mock_run.side_effect = TKSealError("Command failed with exit code 1: kubectl error")

    # Test that TKSealError is raised when kubectl command fails
    with pytest.raises(TKSealError) as exc_info:
        KubeCtl.get_secrets("test-context", "test-namespace")

    assert "Command failed" in str(exc_info.value)
