from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any


MAGIC_KEY = "__real_redact_mapping__"
ALGORITHM = "md5-xor-v1"
_APP_SECRET = b"ReaL Redact local reversible mapping protection"


def write_mapping(path: str | Path, mapping: dict[str, Any]) -> None:
    plaintext = json.dumps(mapping, ensure_ascii=False, indent=2).encode("utf-8")
    payload = {
        MAGIC_KEY: 1,
        "algorithm": ALGORITHM,
        "checksum_md5": hashlib.md5(plaintext).hexdigest(),
        "payload": base64.b64encode(_xor_bytes(plaintext)).decode("ascii"),
    }
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_mapping(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not _is_protected_mapping(data):
        return data

    encrypted = base64.b64decode(data["payload"])
    plaintext = _xor_bytes(encrypted)
    checksum = hashlib.md5(plaintext).hexdigest()
    if checksum != data.get("checksum_md5"):
        raise ValueError("映射文件校验失败，文件可能已损坏。")
    return json.loads(plaintext.decode("utf-8"))


def _is_protected_mapping(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and data.get(MAGIC_KEY) == 1
        and data.get("algorithm") == ALGORITHM
        and isinstance(data.get("payload"), str)
    )


def _xor_bytes(data: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        block = hashlib.md5(_APP_SECRET + counter.to_bytes(8, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(value ^ key for value, key in zip(data, output))
