"""Base object definitions for driver contexts."""

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, model_validator

from aqm_eval.mm_eval.driver.config import Config


class AbstractDriverContext(ABC, BaseModel):
    """Abstract base class for all driver contexts. A "driver context" indicates the origin of the
    configuration.
    """

    model_config = {"frozen": True}

    @cached_property
    @abstractmethod
    def mm_config(self) -> Config: ...

    @cached_property
    def template_dir(self) -> Path:
        return (Path(__file__).parent.parent.parent / "yaml_template").absolute().resolve()

    @model_validator(mode="after")
    def _validate_(self) -> "AbstractDriverContext":
        _ = self.model_dump()
        return self
