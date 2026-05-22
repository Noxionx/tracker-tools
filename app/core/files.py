from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def load_config_file(filename: str, as_json: bool = False) -> Any:
    """Load a file from the application config directory."""

    config_dir = get_settings().resolved_config_dir
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found: {config_dir}")

    with (config_dir / filename).open("r", encoding="utf-8") as file_obj:
        if as_json:
            return json.load(file_obj)
        return file_obj.read()


def write_config_file(filename: str, content: str) -> Path:
    """Write a file in the application config directory with restrictive permissions."""

    config_dir = get_settings().resolved_config_dir
    config_dir.mkdir(parents=True, mode=0o700, exist_ok=True)

    target = config_dir / filename
    with target.open("w", encoding="utf-8") as file_obj:
        file_obj.write(content)

    target.chmod(0o600)
    return target
