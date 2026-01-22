import datetime
from pathlib import Path

from pydantic import Field

from aqm_eval.base import AeBaseModel


class VerifyPair(AeBaseModel):
    actual: Path
    expected: Path


class VerifyContext(AeBaseModel):
    verify_pairs: tuple[VerifyPair,] = Field(min_length=1)
    variables: tuple[str,] = Field(default=("O3", "PM25_TOT",), min_length=1)
    baseline_dir: Path | None = None #tdk:test
    expt_dir: Path | None = None #tdk:test
    tolerance: float = 1e-12

    @classmethod
    def from_cli(cls, kwds: dict) -> "VerifyContext":
        raise NotImplementedError