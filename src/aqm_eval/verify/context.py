import datetime
from pathlib import Path

from aqm_eval.base import AeBaseModel


class VerifyContext(AeBaseModel):
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    cycle_frequency_hours: int
    variables: list[str]
    actual_regex: str
    actual_dir: Path
    expected_regex: str
    expected_dir: Path
    tolerance: float = 1e12

    @classmethod
    def from_cli(cls, kwds: dict) -> "VerifyContext":
        raise NotImplementedError