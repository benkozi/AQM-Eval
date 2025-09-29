"""Base object definitions for driver contexts."""

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, computed_field

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.helpers import PathExisting
from aqm_eval.mm_eval.driver.model import Model
from aqm_eval.mm_eval.driver.package import AbstractEvalPackage


class AbstractDriverContext(ABC, BaseModel):
    """Abstract base class for all driver contexts. A "driver context" indicates the origin of the
    configuration.
    """

    model_config = {"frozen": True}

    @computed_field(description="Path to the Cartopy data directory containing NaturalEarth shapefiles.")
    @cached_property
    @abstractmethod
    def cartopy_data_dir(self) -> PathExisting: ...

    @computed_field(description="Date of the first cycle for MM evaluation in yyyy-mm-dd-HH:MM:SS UTC format.")
    @cached_property
    @abstractmethod
    def date_first_cycle_mm(self) -> str: ...

    @computed_field(description="Date of the last cycle for MM evaluation in yyyy-mm-dd-HH:MM:SS UTC format.")
    @cached_property
    @abstractmethod
    def date_last_cycle_mm(self) -> str: ...

    @cached_property
    @abstractmethod
    def mm_packages(self) -> tuple[AbstractEvalPackage, ...]:
        """
        Returns
        -------
        tuple[AbstractEvalPackage, ...]
            Evaluation packages to initialize and run. An evaluation package is a collection of
            evaluation plots and statistics for specific prognostic variables and observational
            datasets.
        """
        ...

    @cached_property
    @abstractmethod
    def mm_models(self) -> tuple[Model, ...]:
        """
        Returns
        -------
        tuple[Model, ...]
            The models to use in the evaluation. At most, this can contain two models: the
            "evaluation" model and an optional "base" model. If two models are returned,
            "scorecards" can be created.
        """
        ...

    @cached_property
    def mm_model_labels(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            Model labels used for MM plotting.
        """
        return [mm_model.label for mm_model in self.mm_models]

    @cached_property
    def mm_model_titles_j2(self) -> str:
        """
        Returns
        -------
        list[str]
            Model titles used for MM plotting, converted into a format suitable for ``jinja2``.
        """
        return ", ".join([f'"{ii.title}"' for ii in self.mm_models])

    @computed_field(description="Path template to select AirNow observational. Wildcards may be used to select multiple files.")
    @cached_property
    @abstractmethod
    def mm_obs_airnow_fn_template(self) -> str: ...

    @computed_field(
        description="Path to the output directory for MM evaluation. Plot images and statistics files are written here."
    )
    @cached_property
    @abstractmethod
    def mm_output_dir(self) -> PathExisting: ...

    @computed_field(
        description="Path to the MM evaluation run directory where linked data and configuration control files are written."
    )
    @cached_property
    @abstractmethod
    def mm_run_dir(self) -> PathExisting: ...

    @computed_field(description="Path to directory containing template files.")
    @cached_property
    def template_dir(self) -> PathExisting:
        return (Path(__file__).parent.parent.parent / "yaml_template").absolute().resolve()

    @cached_property
    def j2_env(self) -> Environment:
        """
        Returns
        -------
        Environment
            Jinja2 environment for rendering template files.
        """
        searchpath = self.template_dir
        LOGGER(f"creating J2 environment {self.template_dir=}")
        return Environment(
            loader=FileSystemLoader(searchpath=searchpath),
            undefined=StrictUndefined,
        )

    @abstractmethod
    def create_control_configs(self) -> None:
        """Create all configuration files and other artifacts necessary for running the MM
        evaluation.

        Returns
        -------
        None
        """
        ...
