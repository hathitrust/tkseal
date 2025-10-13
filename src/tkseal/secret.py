import base64
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SecretDataPair:
    key: str
    plain_value: str
    encoded_value: str


class Secret:
    def __init__(self, raw: Dict[str, Any]):
        self._raw = raw

    @property
    def name(self) -> str:
        return self._raw["metadata"]["name"]

    @property
    def data(self) -> List[SecretDataPair]:
        result = []
        for key, encoded_value in self._raw.get("data", {}).items():
            plain_value = base64.b64decode(encoded_value).decode()
            result.append(SecretDataPair(
                key=key,
                plain_value=plain_value,
                encoded_value=encoded_value
            ))
        return result


class Secrets:
    def __init__(self, raw_secrets: List[Dict[str, Any]]):
        self.items = [Secret(raw) for raw in raw_secrets]
        self.items = [Secret(raw) for raw in raw_secrets]
