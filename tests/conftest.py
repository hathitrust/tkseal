import json
import os
import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from tkseal.diff import DiffResult
from tkseal.secret_state import SecretState
from tkseal.tk import TKEnvironment

"""
  Test Fixtures for TKSeal

  Fixture Hierarchy:
  ------------------
  1. tk_status_file - Copies tk_status.txt to temp location
  2. temp_tanka_env - Creates temp Tanka directory structure
  3. mock_tk_env - Mock TKEnvironment with values from tk_status.txt
  4. simple_mock_secret_state - Lightweight mock SecretState for unit tests that don't need temp files (Diff, Pull, Seal)
  5. mock_secret_state - Full mock with temp files for integration tests (SecretState and CLI classes)
Notes:
  - All tests use tk_status.txt to ensure consistent context/namespace values.
  """
@pytest.fixture
def tk_status_file(tmp_path):
    """Copy the sample tests/tk_status.txt into a temporary file and return its path."""
    src = Path(__file__).parent / "tk_status.txt"
    dest = tmp_path / "tk_status.txt"
    shutil.copy(src, dest)
    return dest


@pytest.fixture
def temp_tanka_env(tmp_path):
    """Create a temporary Tanka environment directory structure."""
    env_path = tmp_path / "environments" / "test-env"
    env_path.mkdir(parents=True)

    # Create a sample plain_secrets.json
    plain_secrets = [
        {"name": "test-secret", "data": {"username": "admin", "password": "secret123"}}
    ]
    (env_path / "plain_secrets.json").write_text(json.dumps(plain_secrets, indent=2))

    return env_path


@pytest.fixture
def mock_tk_env(mocker, tk_status_file):
    """Create a mock TKEnvironment using values from tests/tk_status.txt."""
    # Parse tk_status.txt to get real context/namespace values
    status_content = tk_status_file.read_text()

    # Extract context and namespace from the file
    context = None
    namespace = None
    for line in status_content.splitlines():
        if line.strip().startswith("Context:"):
            context = line.split(":", 1)[1].strip()
        elif line.strip().startswith("Namespace:"):
            namespace = line.split(":", 1)[1].strip()

    mock_env = mocker.Mock(spec=TKEnvironment)
    mock_env.context = context or "some-context"
    mock_env.namespace = namespace or "some-namespace"
    return mock_env


@pytest.fixture
def simple_mock_secret_state(mocker):
    """
    Lightweight mock SecretState for unit tests that don't need temp files.
    Uses values from tk_status.txt via mock_tk_env.
    """

    mock_state = mocker.Mock(spec=SecretState)
    mock_state.context = "some-context"  # From tk_status.txt
    mock_state.namespace = "some-namespace"  # From tk_status.txt
    mock_state.plain_secrets_file_path = Path("/fake/plain_secrets.json")
    mock_state.sealed_secrets_file_path = Path("/fake/sealed_secrets.json")
    mock_state.plain_secrets.return_value = "[]"
    mock_state.kube_secrets.return_value = "[]"
    mock_state.get_forbidden_secrets.return_value = []  # No forbidden secrets by default
    return mock_state


@pytest.fixture
def mock_secret_state(mocker, tk_status_file, mock_tk_env, temp_tanka_env):
    """
    Create and return a mocked SecretState wired to a temporary Tanka environment
    and the sample `tk_status.txt`.

    - Copies `tk_status_file` into the `temp_tanka_env` directory (as `tk_status.txt`).
    - Builds a mock SecretState that exposes `tk_env`, `plain_secrets_file_path`,
      and basic `plain_secrets` / `kube_secrets` callables.
    - Patches `tkseal.secret_state.SecretState.from_path` to return the mock.
    """
    env_path = Path(temp_tanka_env)
    env_path.mkdir(parents=True, exist_ok=True)

    # copy the sample tk status into the temp tanka env so other code/fixtures can read it
    status_dest = temp_tanka_env / "tk_status.txt"
    shutil.copy(tk_status_file, status_dest)

    mock_secret_state = mocker.Mock()
    mock_secret_state.tk_env = mock_tk_env
    mock_secret_state.plain_secrets_file_path = env_path / "plain_secrets.json"

    # default return values; tests can override these attributes/callables as needed
    mock_secret_state.plain_secrets.return_value = "[]"
    mock_secret_state.kube_secrets.return_value = "[]"
    mock_secret_state.get_forbidden_secrets.return_value = []  # No forbidden secrets by default

    # Patch the factory used by most code paths to create SecretState from a path
    mocker.patch(
        "tkseal.secret_state.SecretState.from_path", return_value=mock_secret_state
    )

    return mock_secret_state


@pytest.fixture
def load_secret_file():
    """Load the test secrets yaml file and return both raw yaml and parsed dict."""
    with open(os.path.join(os.path.dirname(__file__), "secrets.yaml")) as f:
        test_secrets_yaml = f.read()
        test_secrets_dict = yaml.safe_load(test_secrets_yaml)
    return test_secrets_yaml, test_secrets_dict


@pytest.fixture
def sample_plain_secrets():
    """Sample plain_secrets.json content."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "secret123"},
            }
        ],
        indent=2,
    )


@pytest.fixture
def sample_kube_secrets():
    """Sample kube secrets JSON content."""
    return json.dumps(
        [
            {
                "name": "app-secret",
                "data": {"username": "admin", "password": "newsecret456"},
            }
        ],
        indent=2,
    )


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
        ],
        indent=2,
    )


# CLI Testing Fixtures


@pytest.fixture
def mock_external_dependencies(mocker):
    """Mock external dependencies like kubeseal, tk, and kubectl existence checks."""

    mock_kubeseal = mocker.patch("tkseal.kubeseal.KubeSeal.exists")
    mock_tk = mocker.patch("tkseal.tk.TK.exists")
    mock_kubectl = mocker.patch("tkseal.kubectl.KubeCtl.exists")
    return mock_kubeseal, mock_tk, mock_kubectl


@pytest.fixture
def cli_runner():
    """Return a CliRunner instance for CLI testing."""
    return CliRunner()


@pytest.fixture
def diff_result_with_changes():
    """Return a DiffResult with differences."""
    return DiffResult(has_differences=True, diff_output="-old\n+new")


@pytest.fixture
def diff_result_no_changes():
    """Return a DiffResult with no differences."""
    return DiffResult(has_differences=False, diff_output="")


@pytest.fixture
def mock_pull_cli(mocker, diff_result_with_changes):
    """Mock Pull class for CLI tests and return the mock instance."""
    mock_pull = mocker.Mock()
    mock_pull.run.return_value = diff_result_with_changes
    mocker.patch("tkseal.cli.Pull", return_value=mock_pull)
    return mock_pull


@pytest.fixture
def mock_seal_cli(mocker, diff_result_with_changes):
    """Mock Seal class for CLI tests and return the mock instance."""
    mock_seal = mocker.Mock()
    mocker.patch("tkseal.cli.Seal", return_value=mock_seal)

    # Also mock Diff for seal command
    mock_diff = mocker.Mock()
    mock_diff.plain.return_value = diff_result_with_changes
    mocker.patch("tkseal.cli.Diff", return_value=mock_diff)

    return mock_seal, mock_diff
