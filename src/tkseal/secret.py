import base64
import json
from dataclasses import dataclass
from typing import Any, cast

from tkseal import TKSealError
from tkseal.configuration import (
    FORBIDDEN_SECRET_TYPES,
    MANAGED_SECRET_CAREFULLY_TYPES,
    MANAGED_SECRET_TYPES,
)
from tkseal.kubectl import KubeCtl
from tkseal.tk import TKEnvironment


@dataclass
class SecretDataPair:
    key: str
    plain_value: str
    encoded_value: str


class Secret:
    def __init__(self, raw: dict[str, Any]):
        self._raw = raw

    @property
    def name(self) -> str:
        # Use cast to inform mypy (type checker) to treat self._raw["metadata"]["name"] as str
        return cast(str, self._raw["metadata"]["name"])

    @property
    def data(self) -> list[SecretDataPair]:
        result = []
        for key, encoded_value in self._raw.get("data", {}).items():
            plain_value = base64.b64decode(encoded_value).decode()
            result.append(
                SecretDataPair(
                    key=key, plain_value=plain_value, encoded_value=encoded_value
                )
            )
        return result

    @property
    def type(self) -> str:
        return cast(str, self._raw.get("type", ""))


class ForbiddenSecret(Secret):
    """Represents a secret that are not allowed to pull or process due to security policies."""

    def __init__(self, raw: dict[str, Any]):
        super().__init__(raw)

    @property
    def data(self) -> list[SecretDataPair]:
        """Forbidden secrets do not expose data, so accessing this raises an error."""
        raise TKSealError(
            f'Forbidden secret "{self.name}" data cannot be accessed or sealed'
        )


class Secrets:
    # Security check: prevent processing of forbidden types
    # Store forbidden secrets for reporting - [{"secret1":"kubernetes.io/service-account-token"}]
    forbidden_secrets: list[ForbiddenSecret]

    def __init__(self, raw_secrets: dict[str, Any]):
        """Initialize Secrets from YAML-parsed kubectl output format.
        Args:
            raw_secrets: kubectl output dict with 'items' key
        Raises:
            TKSealError: If raw_secrets does not have the items key

        Secret type - Filtering Strategy (to be implemented):

          1. Default to Opaque only (safest, matches Ruby)
          2. Add explicit allow-list for basic-auth and ssh-auth
          3. Add explicit deny-list for service-account-token and bootstrap tokens
          4. Raise error if user tries to include forbidden types (fail-safe)
          5. Log warning when filtering secrets (visibility)
        """

        # Handle kubectl format with the "items" key
        if "items" not in raw_secrets:
            raise TKSealError(
                "Invalid kubectl output: expected dict with 'items' key. "
                f"Got keys: {list(raw_secrets.keys())}"
            )

        self.allowed_types = MANAGED_SECRET_TYPES.union(MANAGED_SECRET_CAREFULLY_TYPES)

        self.forbidden_secrets = Secrets.get_forbidden_secrets(raw_secrets)

        # TODO: If the secret does not have type, assume "Opaque" (Kubernetes default)
        self.items = [
            Secret(raw)
            for raw in raw_secrets["items"]
            if raw.get("type", "Opaque") in self.allowed_types
        ]

    @classmethod
    def for_tk_env(cls, path: str) -> "Secrets":
        """Create Secrets from a Tanka environment path.

        Args:
            path: Path to the Tanka environment

        Returns:
            Secrets object containing all secrets from the Kubernetes cluster

        Raises:
            TKSealError: If there's an error getting secrets from the cluster
        """
        env = TKEnvironment(path)
        raw_secrets = KubeCtl.get_secrets(context=env.context, namespace=env.namespace)
        return cls(raw_secrets)

    @staticmethod
    def get_forbidden_secrets(
        raw_secrets: dict[str, Any],
    ) -> list[ForbiddenSecret]:
        """Create a list of ForbiddenSecret objects.

        Args:
            raw_secrets: kubectl output dict with 'items' key
        Returns:
            List of secrets with forbidden types
        """
        filtered_items: list[ForbiddenSecret] = []
        for raw in raw_secrets.get("items", []):
            if raw.get("type") in FORBIDDEN_SECRET_TYPES:
                filtered_items.append(ForbiddenSecret(raw))
        return filtered_items

    def to_json(self) -> str:
        """Convert secrets to JSON format with decoded plain values.

        Returns:
            Pretty-printed JSON string with structure:
            [
                {
                    "name": "secret-name",
                    "data": {
                        "KEY": "plain_value"
                    }
                }
            ]
        """
        output = []
        for secret in self.items:
            secret_dict = {
                "name": secret.name,
                "data": {pair.key: pair.plain_value for pair in secret.data},
                "type": secret.type,
            }
            output.append(secret_dict)
        return json.dumps(output, indent=2)
