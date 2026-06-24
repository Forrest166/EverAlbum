from pathlib import Path


def get_workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_default_portrait_library_path() -> Path:
    return get_workspace_root() / "portrait_elements"

