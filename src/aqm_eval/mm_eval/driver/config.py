import logging
from copy import deepcopy
from datetime import datetime
from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import Field, model_validator

from aqm_eval.base import AeBaseModel
from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.settings import SETTINGS
from aqm_eval.shared import DateRange, get_str_nested, set_str_nested, update_left


@unique
class ScorecardMethod(StrEnum):
    RMSE = "rmse"
    IOA = "ioa"
    NMB = "nmb"
    NME = "nme"

    def get_mm_prefix(self) -> str:
        mapping = {
            ScorecardMethod.IOA: "pg72",
            ScorecardMethod.NMB: "pg73",
            ScorecardMethod.NME: "pg74",
            ScorecardMethod.RMSE: "pg71",
        }
        return mapping[self]


@unique
class TaskKey(StrEnum):
    """Unique MM task keys."""

    SAVE_PAIRED = "save_paired"
    TIMESERIES = "timeseries"
    TAYLOR = "taylor"
    SPATIAL_BIAS = "spatial_bias"
    SPATIAL_OVERLAY = "spatial_overlay"
    BOXPLOT = "boxplot"
    MULTI_BOXPLOT = "multi_boxplot"
    SCORECARD = "scorecard"
    CSI = "csi"
    STATS = "stats"


@unique
class PackageKey(StrEnum):
    """Unique MM package keys."""

    CHEM = "chem"
    ISH = "ish"
    AQS_PM = "aqs_pm"
    AQS_VOC = "aqs_voc"


@unique
class RunMode(StrEnum):
    STRICT = "strict"
    RESUME = "resume"


@unique
class PlatformKey(StrEnum):
    URSA = "ursa"
    GAEAC6 = "gaeac6"
    DERECHO = "derecho"
    ORION = "orion"
    HERCULES = "hercules"
    LOCAL = "local"


def _is_unique_(v: tuple[Any, ...]) -> tuple[Any, ...]:
    if len(set(v)) != len(v):
        raise ValueError("Values must be unique.")
    return v


class ScorecardConfig(AeBaseModel):
    key: str = Field(exclude=True, description="Unique scorecard identifier.")
    control: str = Field(description="Model to use as the control for the scorecard.")
    sensitivity: str = Field(description="Model to use as the sensitivity for the scorecard.")


class PlatformConfig(AeBaseModel):
    ncores_per_node: int = Field(ge=1, description="Number of cores per node.")


class BatchArgs(AeBaseModel):
    nodes: int = Field(ge=1, default=1, description="Number of nodes to use for the batch job.")
    tasks_per_node: int = Field(ge=1, default=1, description="Number of tasks to run on each node.")
    walltime: str = Field(default="01:00:00", description="Walltime for the batch job.")


class Execution(AeBaseModel):
    batchargs: BatchArgs = Field(default_factory=BatchArgs, description="Batch execution arguments.")


class PackageExecution(AeBaseModel):
    prep: Execution = Field(description="Optional execution settings for the prep/initialization task associated with a package.")
    tasks: dict[TaskKey, Execution] = Field(description="Optional task-level execution overrides.")


class PackageConfig(AeBaseModel):
    key: PackageKey = Field(exclude=True, description="Unique package identifier.")
    observation_template: str | None = Field(
        default=None,
        description="Path to the observation file with appropriate spatiotemporal forecast "
        "coverage. May be null if active is false.",
    )
    observation_variables: dict[str, Any]
    mapping: dict[str, str] = Field(description="Maps model variable names to observation variable names.")
    active: bool = Field(default=True, description="If False, package will not be executed.")
    tasks_to_exclude: tuple[TaskKey, ...] = Field(
        default=tuple(), description="Optional task keys to exclude from package execution."
    )
    execution: PackageExecution = Field(
        default_factory=lambda x: PackageExecution.model_validate({}), description="Optional package execution settings."
    )
    task_overlay: dict[TaskKey, dict]
    task_mm_config: dict[TaskKey, dict]

    @model_validator(mode="after")
    def _validate_model_after_(self) -> "PackageConfig":
        if self.active and self.observation_template is None:
            raise ValueError("observation_template must be set if active is True.")
        return self


class PlotKwargs(AeBaseModel):
    color: str = Field(default="g", description="Plotting color specific to a model. Must be unique for each model.")
    marker: str = Field(default="^", description="Plotting marker style.")
    linestyle: str = Field(default="-", description="Plotting line style.")
    markersize: int = Field(default=4, description="Plotting marker size.")


class TaskDefaults(AeBaseModel):
    execution: Execution = Field(description="Default execution settings for all tasks.")
    save_paired: dict = Field(default={}, description="Default save paired settings (SavePairedTask model).")
    timeseries: dict = Field(default={}, description="Default save paired settings (Plot model).")


class AQMModelConfig(AeBaseModel):
    key: str = Field(exclude=True, description="Unique model identifier.")
    expt_dir: Path = Field(description="Path to the experiment directory containing diag and phy netCDF files.")
    title: str = Field(description="A unique model title to use when creating MM evaluation plots.")
    plot_kwargs: PlotKwargs = Field(description="Plotting keyword arguments to use when creating MM evaluation plots.")
    is_host: bool = Field(
        default=False,
        description="If true, this is the 'host' model. A 'host' model contains the workflow configuration for the evaluation. "
        "An evaluation needs at least one host model.",
    )
    type: str = "rrfs"
    kwargs: dict[str, Any] = {"surf_only": True, "mech": "cb6r3_ae6_aq"}
    radius_of_influence: float = 20000.0
    variables: Any | None = None
    projection: Any | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_model_(cls, values: dict) -> dict:
        if values.get("title") is None:
            values["title"] = values["key"]
        return values


class AQMConfig(AeBaseModel):
    active: bool = Field(
        description="Enable or disable the AQM evaluation. Clients can respond to this value to determine if the UFS-AQM "
        "evaluation should run."
    )
    no_forecast: bool = Field(
        description="If true, the evaluation runs 'offline' with no forecast expected. The host experiment is excluded from "
        "the evaluation. If false, the host experiment is included in the evaluation. Following the forecast task, "
        "the evaluation will run."
    )
    models: dict[str, AQMModelConfig] = Field(
        description="Dictionary of model configurations to evaluate. Keys are unique model identifiers. Model 'stems' must "
        "be unique."
    )
    packages: dict[PackageKey, PackageConfig] = Field(
        min_length=1, description="Dictionary of evalution package configurations. Keys are PackageKey enum values."
    )
    task_defaults: TaskDefaults = Field(description="Default settings for evaluation tasks.")
    scorecards: dict[str, ScorecardConfig] = Field(
        description="Dictionary of scorecard configurations for model sensitivity analysis. Keys are unique scorecard identifiers."
    )
    run_mode: RunMode = Field(
        description="Execution mode: 'strict' (fail if run or output directories exist) or 'resume' (continue from previous run "
        "when possible; useful to avoid re-generating pre-processed data files)."
    )

    @cached_property
    def enable_scorecards(self) -> bool:
        return len(self.scorecards) > 0

    @cached_property
    def host_model(self) -> dict[str, AQMModelConfig]:
        for k, v in self.models.items():
            if v.is_host:
                return {k: v}
        raise ValueError("No host model found.")

    @cached_property
    def n_models_to_evaluate(self) -> int:
        n_models = len(self.models)
        if self.no_forecast:
            n_models -= 1
        return n_models

    @model_validator(mode="before")
    @classmethod
    def _validate_model_before_(cls, values: dict) -> dict:
        for target in ["models", "packages", "scorecards"]:
            for k, v in values[target].items():
                if isinstance(values[target][k], Mapping):
                    values[target][k]["key"] = k
        if len(values.get("models", {})) == 0:
            raise ValueError("At least one model must be specified.")
        return values

    @model_validator(mode="after")
    def _validate_model_after_(self) -> "AQMConfig":
        for k, v in self.scorecards.items():
            if v.control not in self.models or v.sensitivity not in self.models:
                raise ValueError(f"Scorecard key={k} references non-existent model {v.control=} or {v.sensitivity=}.")
            if self.no_forecast and list(self.host_model.keys())[0] in [v.control, v.sensitivity]:
                raise ValueError(f"Host model cannot be used for scorecard {k} since no_forecast is True.")

        self._validate_models_after_()

        return self

    def _validate_models_after_(self) -> None:
        values = self.models

        for target in values.keys():
            for k in values.keys():
                if target == k:
                    continue
                if k[0 : len(target)] == target:
                    raise ValueError(f"Model stems must be unique for wildcard selections. '{target}' and '{k}' are an issue.")

        for k, v in values.items():
            if v.key != k:
                raise ValueError(f"Model key={k} does not match value.key={v.key}.")

        is_host = set([k for k, v in values.items() if v.is_host])
        if len(is_host) != 1:
            raise ValueError(f"Only one model can be host. Found {is_host}.")

        if len(set([ii.title for ii in values.values()])) != len(values):
            raise ValueError("Model titles must be unique.")

        if self.no_forecast:
            LOGGER("no forecast is True, so host model's color will not be considered", level=logging.WARNING)
            plot_colors_to_check = [v.plot_kwargs.color for v in values.values() if not v.is_host]
            n_to_check = len(values) - 1
        else:
            plot_colors_to_check = [v.plot_kwargs.color for v in values.values()]
            n_to_check = len(values)
        if len(set(plot_colors_to_check)) != n_to_check:
            plot_colors = {k: v.plot_kwargs.color for k, v in values.items()}
            raise ValueError(f"models[].plot_kwargs.color must be unique for each model. {plot_colors=}")


class Config(AeBaseModel):
    model_config = {"extra": "forbid"}

    start_datetime: str = Field(description="Evaluation start time in yyyy-mm-dd-HH:MM:SS UTC format.")
    end_datetime: str = Field(description="Evaluation end time in yyyy-mm-dd-HH:MM:SS UTC format.")
    cartopy_data_dir: Path = Field(
        description="Path to the Cartopy data directory. Often ~/.local/share/cartopy. Can be found programmatically via "
        "import cartopy.config; print(cartopy.config['data_dir'])."
    )
    output_dir: Path = Field(
        description="Path to the output directory. This directory will contain paired files, generated plots and statistics files."
    )
    run_dir: Path = Field(
        description="Path to the run directory. This directory will contain configuration files and any linked or pre-processed "
        "data files."
    )
    aqm: AQMConfig = Field(description="Configuration specific to UFS-AQM.")
    platform_defaults: dict[PlatformKey, PlatformConfig] = Field(description="Platform configuration defaults.")

    _key: str = "melodies_monet_parm"

    @cached_property
    def date_range(self) -> DateRange:
        start = datetime.strptime(self.start_datetime, "%Y-%m-%d-%H:%M:%S")
        end = datetime.strptime(self.end_datetime, "%Y-%m-%d-%H:%M:%S")
        return DateRange(start=start, end=end)

    def to_yaml(self) -> dict:
        ret = self.model_dump(mode="json")
        ret = {self._key: ret}
        return ret

    @classmethod
    def from_yaml(cls, data: dict) -> "Config":
        return cls.model_validate(data[cls.get_key()])

    @classmethod
    def from_default_yaml(cls, platform_key: PlatformKey, overrides: dict) -> "Config":
        raw = (SETTINGS.eval_template_dir / "config-default.yaml").read_text()
        data = yaml.safe_load(raw)[cls.get_key()]
        update_left(data, overrides)

        root_aqm = data["aqm"]
        if len([v for v in root_aqm["models"].values() if v.get("is_host", False)]) != 1:
            LOGGER("removing default host model (key=eval) since another was provided", level=logging.WARNING)
            root_aqm["models"].pop("eval")

        for package_key in PackageKey:
            kp = f"aqm.packages.{package_key.value}.execution.prep.batchargs.tasks_per_node"
            actual = get_str_nested(data, kp)
            if actual == "auto":
                data_kp = f"platform_defaults.{platform_key.value}.ncores_per_node"
                set_str_nested(data, kp, get_str_nested(data, data_kp))
            for task_key, task_value in get_str_nested(data, f"aqm.packages.{package_key.value}.execution.tasks").items():
                if "tasks_per_node" not in task_value["batchargs"]:
                    task_value["batchargs"]["tasks_per_node"] = get_str_nested(
                        data, f"platform_defaults.{platform_key.value}.ncores_per_node"
                    )

            for task_key in TaskKey:
                task_plot_lhs = deepcopy(root_aqm["task_defaults"].setdefault(task_key.value, {}))
                task_plot_rhs = (
                    root_aqm["packages"][package_key.value].setdefault("task_overlay", {}).setdefault(task_key.value, {})
                )
                update_left(task_plot_lhs, task_plot_rhs)
                root_aqm["packages"][package_key.value].setdefault("task_mm_config", {})[task_key.value] = task_plot_lhs

        if root_aqm["task_defaults"]["execution"]["batchargs"]["tasks_per_node"] == "auto":
            root_aqm["task_defaults"]["execution"]["batchargs"]["tasks_per_node"] = get_str_nested(
                data, f"platform_defaults.{platform_key.value}.ncores_per_node"
            )

        return cls.from_yaml({cls.get_key(): data})

    @classmethod
    def get_key(cls) -> str:
        return cls._key.default  # type: ignore[attr-defined]

    @model_validator(mode="after")
    def _validate_model_after_(self) -> "Config":
        _ = self.date_range
        return self
