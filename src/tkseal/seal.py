"""Seal module for converting plain secrets to sealed secrets."""

import json

from tkseal.kubeseal import KubeSeal
from tkseal.secret_state import SecretState


class Seal:
    """Handles sealing of plain secrets using kubeseal.

    This class converts plain_secrets.json to sealed_secrets.json by:
    1. Reading plain secrets from the environment
    2. Encrypting each secret value using kubeseal
    3. Creating SealedSecret resources in Kubernetes format
    4. Writing sealed secrets to sealed_secrets.json
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

        Reads plain_secrets.json, encrypts each secret value using kubeseal,
        creates SealedSecret resources, and writes to sealed_secrets.json.

        Raises:
            TKSealError: If sealing or file operations fail
            json.JSONDecodeError: If plain_secrets.json is malformed
        """
        # Read and parse plain secrets
        plain_secrets_text = self.secret_state.plain_secrets()
        plain_secrets = json.loads(plain_secrets_text)

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
                        }
                    },
                    "encryptedData": encrypted_data,
                },
            }
            sealed_secrets.append(sealed_secret)

        # Write sealed secrets to file
        sealed_json = json.dumps(sealed_secrets, indent=2)
        self.secret_state.sealed_secrets_file_path.write_text(sealed_json)
