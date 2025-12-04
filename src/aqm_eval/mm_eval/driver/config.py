import logging
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


def _is_unique_(v: tuple[Any, ...]) -> tuple[Any, ...]:
    if len(set(v)) != len(v):
        raise ValueError("Values must be unique.")
    return v


class ScorecardConfig(AeBaseModel):
    key: str = Field(exclude=True)
    control: str
    sensitivity: str


class PlatformConfig(AeBaseModel):
    ncores_per_node: int = Field(ge=1)


class BatchArgs(AeBaseModel):
    nodes: int = Field(ge=1, default=1)
    tasks_per_node: int = Field(ge=1, default=1)
    walltime: str = Field(default="01:00:00")


class Execution(AeBaseModel):
    batchargs: BatchArgs = Field(default_factory=BatchArgs)


class PackageExecution(AeBaseModel):
    prep: Execution
    tasks: dict[TaskKey, Execution]


class PackageConfig(AeBaseModel):
    key: PackageKey = Field(exclude=True)
    observation_template: str | None = Field(default=None, description="May be null if active is false.")
    mapping: dict[str, str]
    active: bool = True
    tasks_to_exclude: tuple[TaskKey, ...] = tuple()
    execution: PackageExecution = Field(default_factory=lambda x: PackageExecution.model_validate({}))

    @model_validator(mode="after")
    def _validate_model_after_(self) -> "PackageConfig":
        if self.active and self.observation_template is None:
            raise ValueError("observation_template must be set if active is True.")
        return self


class PlotKwargs(AeBaseModel):
    color: str = "g"
    marker: str = "^"
    linestyle: str = "-"
    markersize: int = 4


class TaskDefaults(AeBaseModel):
    execution: Execution


class AQMModelConfig(AeBaseModel):
    key: str = Field(exclude=True)
    expt_dir: Path
    title: str
    plot_kwargs: PlotKwargs
    # role: ModelRole = ModelRole.UNDEFINED
    is_eval_target: bool = True
    is_host: bool = False
    type: str = "rrfs"
    kwargs: dict[str, Any] = {"surf_only": True, "mech": "cb6r3_ae6_aq"}
    radius_of_influence: float = 20000
    variables: Any | None = None
    projection: Any | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_model_(cls, values: dict) -> dict:
        if values.get("title") is None:
            values["title"] = values["key"]
        return values


class AQMConfig(AeBaseModel):
    active: bool
    no_forecast: bool = False
    models: dict[str, AQMModelConfig]
    packages: dict[PackageKey, PackageConfig] = Field(min_length=1)
    task_defaults: TaskDefaults
    scorecards: dict[str, ScorecardConfig]
    run_mode: RunMode

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
    start_datetime: str = Field(description="Evaluation start time in yyyy-mm-dd-HH:MM:SS UTC format.")
    end_datetime: str = Field(description="Evaluation end time in yyyy-mm-dd-HH:MM:SS UTC format.")
    cartopy_data_dir: Path = Field(description="Path to the Cartopy data directory.")
    output_dir: Path
    run_dir: Path
    aqm: AQMConfig
    platform_defaults: dict[PlatformKey, PlatformConfig]

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
