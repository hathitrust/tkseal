import base64
import json
from dataclasses import dataclass
from typing import Any, cast

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


class Secrets:
    def __init__(self, raw_secrets: list[dict[str, Any]] | dict[str, Any]):
        """Initialize Secrets from either a list or kubectl output format.
        Args:
            raw_secrets: Either a list of secret dicts, or a kubectl output dict with 'items' key
        """
        # Handle kubectl format with "items" key
        if isinstance(raw_secrets, dict) and "items" in raw_secrets:
            secret_list = raw_secrets["items"]
        else:
            secret_list = raw_secrets

        self.items = [Secret(raw) for raw in secret_list]

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
            }
            output.append(secret_dict)
        return json.dumps(output, indent=2)
