from pathlib import Path
import json
from typing import Any


def save(path: Path, data: dict[str, Any] | str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)


def read(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
