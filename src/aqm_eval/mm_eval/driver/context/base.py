"""Base object definitions for driver contexts."""

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, computed_field

from aqm_eval.shared import PathExisting


class AbstractDriverContext(ABC, BaseModel):
    """Abstract base class for all driver contexts. A "driver context" indicates the origin of the
    configuration.
    """

    model_config = {"frozen": True}

    @computed_field
    @cached_property
    @abstractmethod
    def mm_base_model_expt_dir(self) -> PathExisting | None: ...

    @computed_field
    @cached_property
    @abstractmethod
    def mm_eval_model_expt_dir(self) -> PathExisting: ...

    @computed_field
    @cached_property
    @abstractmethod
    def link_simulation(self) -> tuple[str, ...]: ...

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
