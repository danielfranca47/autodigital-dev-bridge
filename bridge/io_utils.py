from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def atomic_write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    fd, temp_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def fill_placeholders(template: str, values: dict[str, str]) -> str:
    content = template
    for key, value in values.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content
