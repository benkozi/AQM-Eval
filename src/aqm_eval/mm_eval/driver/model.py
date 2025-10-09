"""Defines the model objects used when generating MM configuration files."""

from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.helpers import PathExisting, create_symlinks


@unique
class ModelRole(StrEnum):
    """Model role when generating configuration files."""

    EVAL = "eval"
    BASE = "base"


class Model(BaseModel):
    """Defines a model used for generating MM configuration files."""

    model_config = {"frozen": True}

    expt_dir: PathExisting = Field(description="Experiment directory containing model output.")
    label: str = Field(description="Model label used to uniquely identify the model in MM configuration files.")
    title: str = Field(description="Model title used in MM plots.")
    prefix: str = Field(description="File prefix used when creating symlinks to model output files.")
    role: ModelRole = Field(description="Model role when generating configuration files.")
    cycle_dir_template: tuple[str, ...] = Field(description="Templates for selecting model output directories.")
    dyn_file_template: tuple[str, ...] = Field(description="Templates for selecting model output dynamics files.")
    link_alldays_path: Path = Field(description="Path to directory where symlinks to model output files will be created.")

    @computed_field(description="Template for selecting symlinked data files.")
    @cached_property
    def link_alldays_path_template(self) -> str:
        ret = str(self.link_alldays_path / f"{self.prefix}*.nc")
        LOGGER(f"link_alldays_path_template: {ret}")
        return ret

    @computed_field(description="Determines a model's color based on its role.")
    @cached_property
    def plot_kwargs_color(self) -> str:
        match self.role:
            case ModelRole.EVAL:
                return "forestgreen"
            case ModelRole.BASE:
                return "magenta"
            case _:
                raise ValueError(f"Unknown role: {self.role}")

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
            self.expt_dir,
            self.link_alldays_path,
            self.prefix,
            self.cycle_dir_template,
            self.dyn_file_template,
        )
