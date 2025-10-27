from tkseal.diff import Diff, DiffResult
from tkseal.secret_state import SecretState


class Pull:
    """Handles pulling secrets from Kubernetes cluster to local files.

    This class coordinates the process of retrieving secrets from a Kubernetes
    cluster and saving them to the local plain_secrets.json file.
    """

    def __init__(self, secret_state: SecretState):
        """Initialize Pull with a SecretState instance.

        Args:
            secret_state: SecretState instance for the environment
        """
        self.secret_state = secret_state

    def run(self) -> DiffResult:
        """Show differences between local and cluster secrets.

        This method displays what would change in the local plain_secrets.json
        file if secrets were pulled from the cluster.

        Returns:
            DiffResult: Result containing different information

        Raises:
            TKSealError: If there's an error retrieving secrets from the cluster
        """
        diff = Diff(self.secret_state)
        return diff.pull()

    def write(self) -> None:
        """Write cluster secrets to the plain_secrets.json file.

        This method retrieves secrets from the Kubernetes cluster and writes
        them to the local plain_secrets.json file, overwriting any existing content.

        Raises:
            TKSealError: If there's an error retrieving secrets from cluster
            PermissionError: If there's an error writing to the file
            OSError: If there's an I/O error writing to the file
        """
        kube_secrets = self.secret_state.kube_secrets()
        self.secret_state.plain_secrets_file_path.write_text(kube_secrets)
