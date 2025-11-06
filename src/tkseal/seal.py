"""Seal module for converting plain secrets to sealed secrets."""

import json

from tkseal import TKSealError
from tkseal.configuration import PLAIN_SECRETS_FILE
from tkseal.kubeseal import KubeSeal
from tkseal.secret_state import SecretState
from tkseal.serializers import deserialize_secrets, serialize_secrets


class Seal:
    """Handles sealing of plain secrets using kubeseal.

    This class converts plain_secrets files to sealed_secrets files by:
    1. Reading plain secrets from the environment (JSON or YAML)
    2. Encrypting each secret value using kubeseal
    3. Creating SealedSecret resources in Kubernetes format
    4. Writing sealed secrets in the specified format (JSON or YAML)
    """

    def __init__(self, secret_state: SecretState):
        """Initialize Seal with a SecretState instance.

        Args:
            secret_state: SecretState instance for the environment
        """
        self.secret_state = secret_state

    def kubeseal(self, name: str, value: str) -> str:
        """Seal a secret value using kubeseal.

        Args:
            name: Secret name
            value: Plain text value to seal

        Returns:
            str: Sealed (encrypted) value

        Raises:
            TKSealError: If sealing fails
        """
        return KubeSeal.seal(
            context=self.secret_state.context,
            namespace=self.secret_state.namespace,
            name=name,
            value=value,
        )

    def run(self) -> None:
        """Convert plain secrets to sealed secrets.

        Reads plain_secrets file (JSON or YAML), encrypts each secret value using kubeseal,
        creates SealedSecret resources, and writes to sealed_secrets file in the specified format.

        Raises:
            TKSealError: If sealing or file operations fail
        """
        # Read and parse plain secrets
        plain_secrets_text = self.secret_state.plain_secrets()

        # Check if plain_secrets_text is empty or exists
        if not plain_secrets_text or plain_secrets_text.strip() == "":
            raise TKSealError(
                f"No plain secrets found. Please create {PLAIN_SECRETS_FILE}.{self.secret_state.format} "
                f"or run 'tkseal pull' first."
            )

        # Deserialize from the file format (could be JSON or YAML)
        try:
            plain_secrets = deserialize_secrets(
                plain_secrets_text, self.secret_state.format
            )
        except (json.JSONDecodeError, Exception) as e:
            raise TKSealError(
                f"Invalid format in plain_secrets file: {str(e)}"
            ) from e

        # Process each secret
        sealed_secrets = []
        for secret in plain_secrets:
            # Seal each data key-value pair
            encrypted_data = {}
            for key, value in secret["data"].items():
                encrypted_data[key] = self.kubeseal(name=secret["name"], value=value)

            # Create SealedSecret structure
            sealed_secret = {
                "kind": "SealedSecret",
                "apiVersion": "bitnami.com/v1alpha1",
                "metadata": {
                    "name": secret["name"],
                    "namespace": self.secret_state.namespace,
                },
                "spec": {
                    "template": {
                        "metadata": {
                            "name": secret["name"],
                            "namespace": self.secret_state.namespace,
                        },
                        # Preserve the secret type if specified in the plain_secrets file
                        **({"type": secret["type"]} if "type" in secret else {}),
                    },
                    "encryptedData": encrypted_data,
                },
            }
            sealed_secrets.append(sealed_secret)

        # Serialize and write sealed secrets to file in the specified format
        sealed_output = serialize_secrets(sealed_secrets, self.secret_state.format)
        self.secret_state.sealed_secrets_file_path.write_text(sealed_output)
