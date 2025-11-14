import datetime
import logging
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Annotated, Any, Iterator, Mapping

import numpy as np
from pydantic import BaseModel, BeforeValidator, PlainSerializer

from aqm_eval.logging_aqm_eval import LOGGER


def assert_path_exists(path: Path | str) -> Path:
    path = Path(path)
    if not path.exists():
        LOGGER(exc_info=FileNotFoundError(f"path does not exist: {path}"))
    return path


PathExisting = Annotated[Path, BeforeValidator(assert_path_exists), PlainSerializer(lambda x: str(x), return_type=str)]


def assert_directory_exists(path: Path | str) -> PathExisting:
    path = assert_path_exists(path)
    if not path.is_dir():
        LOGGER(exc_info=ValueError(f"path is not a directory: {path}"))
    return path


PathExistingDir = Annotated[Path, BeforeValidator(assert_directory_exists), PlainSerializer(lambda x: str(x), return_type=str)]


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


def ncdump(path: Path) -> None:
    result = subprocess.check_output(["ncdump", "-h", str(path)])
    print(result.decode())


def calc_2d_chunks(dims: dict[str, int], n_chunks: int) -> dict[str, int]:
    if n_chunks < 1:
        n_chunks = 1
    per_dim = np.ceil(np.sqrt(n_chunks))
    chunks = {k: int(np.ceil(v / per_dim)) for k, v in dims.items()}
    return chunks


class DateRange(BaseModel):
    start: datetime.datetime
    end: datetime.datetime

    def iter_by_step(self, step: datetime.timedelta = datetime.timedelta(days=1)) -> Iterator[datetime.datetime]:
        curr_dt = deepcopy(self.start)
        while curr_dt <= self.end:
            try:
                yield deepcopy(curr_dt)
            finally:
                curr_dt += step

    @staticmethod
    def to_srw_str(target: datetime.datetime) -> str:
        return target.strftime("%Y%m%d%H")


def update_left(data_left: dict, data_right: dict) -> None:
    for key, value in data_right.items():
        if isinstance(data_left.get(key), Mapping):
            update_left(data_left[key], value)
        else:
            data_left[key] = value


def get_str_nested(data: dict, key: str) -> Any:
    for k in key.split("."):
        data = data[k]
    return data


def set_str_nested(data: dict, key: str, value: Any) -> None:
    keys = key.split(".")
    for key in keys[:-1]:
        data = data[key]
    data[keys[-1]] = value
