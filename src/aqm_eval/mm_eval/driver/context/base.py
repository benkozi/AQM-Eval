"""Base object definitions for driver contexts."""

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, computed_field

from aqm_eval.mm_eval.driver.config import Config
from aqm_eval.shared import PathExisting


class AbstractDriverContext(ABC, BaseModel):
    """Abstract base class for all driver contexts. A "driver context" indicates the origin of the
    configuration.
    """

    model_config = {"frozen": True}

    @cached_property
    @abstractmethod
    def mm_config(self) -> Config: ...

    @computed_field(description="Path to directory containing template files.")
    @cached_property
    def template_dir(self) -> PathExisting:
        return (Path(__file__).parent.parent.parent / "yaml_template").absolute().resolve()
