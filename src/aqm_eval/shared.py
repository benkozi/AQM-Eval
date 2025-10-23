import logging
import subprocess
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from pydantic import BeforeValidator

from aqm_eval.logging_aqm_eval import LOGGER


def assert_path_exists(path: Path | str) -> Path:
    path = Path(path)
    if not path.exists():
        LOGGER(exc_info=FileNotFoundError(f"path does not exist: {path}"))
    return path


def _format_path_existing_(value: Path | str) -> Path:
    LOGGER(f"formatting {value}", level=logging.DEBUG)
    ret = Path(value)
    if not ret.exists():
        LOGGER(exc_info=FileNotFoundError(f"path does not exist: {ret}"))
    return ret


PathExisting = Annotated[Path, BeforeValidator(_format_path_existing_)]


def get_or_create_path(path: str | Path, **kwargs: Any) -> Path:
    path = Path(path)
    if not path.exists():
        LOGGER(f"creating path: {path}", level=logging.DEBUG)
        defaults = dict(exist_ok=True, parents=True)
        defaults.update(kwargs)
        path.mkdir(**defaults)
    return path


def assert_file_exists(path: Path | str) -> Path:
    path = assert_path_exists(path)
    if not path.is_file():
        LOGGER(exc_info=ValueError(f"path is not a file: {path}"))
    return path


def assert_directory_exists(path: Path | str) -> PathExisting:
    path = assert_path_exists(path)
    if not path.is_dir():
        LOGGER(exc_info=ValueError(f"path is not a directory: {path}"))
    return path


def ncdump(path: Path) -> None:
    result = subprocess.check_output(["ncdump", "-h", str(path)])
    print(result.decode())


def calc_2d_chunks(dims: dict[str, int], n_chunks: int) -> dict[str, int]:
    if n_chunks < 1:
        n_chunks = 1
    per_dim = np.ceil(np.sqrt(n_chunks))
    chunks = {k: int(np.ceil(v / per_dim)) for k, v in dims.items()}
    return chunks
