from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@unique
class LogLevel(StrEnum):
    """Log level enum. Used to wrap standard `logging` levels.

    Attributes
    ----------
    INFO : str
        Equivalent to `logging.INFO`.
    DEBUG : str
        Equivalent to `logging.DEBUG`.
    """

    INFO = "info"
    DEBUG = "debug"


class AQM_EvalSettings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)

    aqm_eval_log_level: LogLevel = LogLevel.INFO

    slurm_ntasks_per_node: int = 1
    slurm_nnodes: int = 1

    @computed_field
    @cached_property
    def dask_num_workers(self) -> int:
        targets = (self.slurm_ntasks_per_node,)
        ppn = 1
        for target in targets:
            if target is not None:
                ppn = target
        return ppn * self.slurm_nnodes

    @computed_field
    @cached_property
    def eval_template_dir(self) -> Path:
        return Path(__file__).parent / "mm_eval" / "mm_eval_config"

    @field_validator("aqm_eval_log_level", mode="before")
    @classmethod
    def _validate_aqm_eval_log_level_(cls, value: str) -> LogLevel:
        return LogLevel(value.lower())


SETTINGS = AQM_EvalSettings()
