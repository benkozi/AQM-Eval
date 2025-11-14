"""Defines the model objects used when generating MM configuration files."""

from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.config import AQMModelConfig
from aqm_eval.mm_eval.driver.helpers import create_symlinks
from aqm_eval.shared import DateRange


class Model(BaseModel):
    """Defines a model used for generating MM configuration files."""

    model_config = {"frozen": True}

    cfg: AQMModelConfig
    file_template: tuple[str, ...] = Field(description="Templates for selecting model output files.")
    link_alldays_path: Path = Field(description="Path to directory where symlinks to model output files will be created.")
    date_range: DateRange

    @computed_field(description="Template for selecting symlinked data files.")
    @cached_property
    def link_alldays_path_template(self) -> str:
        ret = str(self.link_alldays_path / f"{self.label}*.nc")
        LOGGER(f"link_alldays_path_template: {ret}")
        return ret

    @cached_property
    def label(self) -> str:
        return self.cfg.key

    @log_it
    def create_symlinks(
        self,
    ) -> None:
        """
        Create symlinks to model output files.

        Returns
        -------
        None
        """
        create_symlinks(
            self.cfg.expt_dir,
            self.link_alldays_path,
            self.label,
            self.date_range,
            self.file_template,
        )
