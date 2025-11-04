import base64
import json
from dataclasses import dataclass
from typing import Any, cast

from tkseal import TKSealError
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
    def __init__(self, raw_secrets: dict[str, Any]):
        """Initialize Secrets from YAML-parsed kubectl output format.
        Args:
            raw_secrets: kubectl output dict with 'items' key
        Raises:
            TKSealError: If raw_secrets does not have the items key
        """

        # Handle kubectl format with the "items" key
        if "items" not in raw_secrets:
            raise TKSealError(
                "Invalid kubectl output: expected dict with 'items' key. "
                f"Got keys: {list(raw_secrets.keys())}"
            )

        self.items = [Secret(raw) for raw in raw_secrets["items"]]

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
