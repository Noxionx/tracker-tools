import os
import json
from pathlib import Path
import importlib

default_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def list_scrappers():
    folder = Path(__file__).parent.joinpath("scrappers")
    return [f.stem for f in folder.glob("*.py") if not f.name.startswith("_")]


def load_scrapper(name):
    return importlib.import_module(f"scrappers.{name}")


def _get_config_dir() -> Path:
    config_dir = os.getenv("CONFIG_DIR", ".config")
    path = Path(config_dir)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    return path


def load_file(filename, is_json: bool = False):
    config_dir = _get_config_dir()
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found : {config_dir}")
    with open(config_dir / filename, "r") as f:
        if is_json:
            return json.load(f)
        else:
            return f.read()


def write_file(filename, content):
    config_dir = _get_config_dir()
    if not config_dir.exists():
      config_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    file_path = config_dir / filename
    with open(file_path, "w") as f:
        f.write(content)
    file_path.chmod(0o600)


class UnknownTrackerError(Exception):
    pass


class ScrappingError(Exception):
    pass


class MissingCredentialsError(Exception):
    pass
