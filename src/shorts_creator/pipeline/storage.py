from pathlib import Path
import json
from typing import Any


def save(path: Path, data: dict[str, Any] | str) -> None:
    with open(path, "w") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f)


def read(path: Path) -> str:
    with open(path) as f:
        return f.read()
