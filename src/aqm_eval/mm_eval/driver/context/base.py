"""Base object definitions for driver contexts."""

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from pydantic import model_validator

from aqm_eval.base import AeBaseModel
from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.config import Config


class AbstractDriverContext(ABC, AeBaseModel):
    """Abstract base class for all driver contexts. A "driver context" indicates the origin of the
    configuration.
    """

    @cached_property
    @abstractmethod
    def mm_config(self) -> Config: ...

    @cached_property
    def template_dir(self) -> Path:
        return (Path(__file__).parent.parent.parent / "yaml_template").absolute().resolve()

    @model_validator(mode="after")
    def _validate_(self) -> "AbstractDriverContext":
        if not self.mm_config.aqm.active:
            LOGGER(exc_info=ValueError("AQM evaluation is not active"))
        _ = self.model_dump()
        return self
