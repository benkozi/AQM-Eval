from datetime import datetime
from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, Field, field_validator, model_validator

from aqm_eval.shared import DateRange, PathExistingDir


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
    SCORECARD_RMSE = "scorecard_rmse"
    SCORECARD_IOA = "scorecard_ioa"
    SCORECARD_NMB = "scorecard_nmb"
    SCORECARD_NME = "scorecard_nme"
    CSI = "csi"
    STATS = "stats"


@unique
class PackageKey(StrEnum):
    """Unique MM package keys."""

    CHEM = "chem"
    ISH = "ish"
    AQS_PM = "aqs_pm"
    AQS_VOC = "aqs_voc"


def _is_unique_(v: tuple[Any, ...]) -> tuple[Any, ...]:
    if len(set(v)) != len(v):
        raise ValueError("Values must be unique.")
    return v


class BatchArgs(BaseModel):
    model_config = {"frozen": True}

    nodes: int = Field(ge=1, default=1)
    tasks_per_node: int = Field(ge=1, default=1)
    walltime: str = Field(default="01:00:00")


class Execution(BaseModel):
    model_config = {"frozen": True}

    batchargs: BatchArgs = Field(default_factory=BatchArgs)


class PackageExecution(BaseModel):
    model_config = {"frozen": True}

    prep: Execution
    tasks: dict[TaskKey, Execution]


class PackageConfig(BaseModel):
    model_config = {"frozen": True}

    key: PackageKey = Field(exclude=True)
    observation_template: str  # tdk: can be null if active is false
    mapping: dict[str, str]
    active: bool = True
    tasks_to_exclude: tuple[TaskKey, ...] = tuple()
    execution: PackageExecution = Field(default_factory=lambda x: PackageExecution.model_validate({}))

    @model_validator(mode="before")
    @classmethod
    def _validate_model_(cls, values: dict) -> dict:
        if values.get("mapping") is None:
            match values["key"]:
                case PackageKey.CHEM:
                    mapping = {
                        "o3_ave": "OZONE",
                        "pm25_ave": "PM2.5",
                        "no2_ave": "NO2",
                        "co": "CO",
                    }
                case PackageKey.ISH:
                    mapping = {
                        "tmp2m": "temp",
                        "ws10m": "ws",
                        "dew_temp": "dew_pt_temp",
                    }
                case PackageKey.AQS_VOC:
                    mapping = {
                        "etha": "ETHANE",
                        "prpa": "PROPANE",
                        "benzene": "BENZENE",
                        "tol": "TOLUENE",
                        "isop": "ISOPRENE",
                    }
                case PackageKey.AQS_PM:
                    mapping = {
                        "pm25_so4": "SO4f",
                        "pm25_no3": "NO3f",
                        "pm25_nh4": "NH4+f",
                        "pm25_ec": "ECf",
                        "pm25_oc": "OCPM2.5LCTOT",
                    }

                case _:
                    raise ValueError(values["key"])
            values["mapping"] = mapping

        return values


class PlotKwargs(BaseModel):
    model_config = {"frozen": True}

    color: str = "g"
    marker: str = "^"
    linestyle: str = "-"
    markersize: int = 4

    _possible_colors: tuple[str, ...] = ("g", "m", "k", "r", "b", "y")


class TaskDefaults(BaseModel):
    model_config = {"frozen": True}

    execution: Execution


class AQMModelConfig(BaseModel):
    model_config = {"frozen": True}

    key: str = Field(exclude=True)
    expt_dir: PathExistingDir
    title: str  # tdk: unique in coll
    plot_kwargs: PlotKwargs
    is_host: bool = False  # tdk: only one model needs to be host = true but must be one
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


class AQMConfig(BaseModel):
    model_config = {"frozen": True}

    models: dict[str, AQMModelConfig] = Field(max_length=4)
    packages: dict[PackageKey, PackageConfig] = Field(min_length=1)
    task_defaults: TaskDefaults
    no_forecast: bool = False

    @cached_property
    def host_model(self) -> dict[str, AQMModelConfig]:
        for k, v in self.models.items():
            if v.is_host:
                return {k: v}
        raise ValueError("No host model found.")

    @model_validator(mode="before")
    @classmethod
    def _validate_model_before_(cls, values: dict) -> dict:
        for target in ["models", "packages"]:
            for k, v in values[target].items():
                if isinstance(values[target][k], Mapping):
                    values[target][k]["key"] = k
        return values

    @field_validator("models", mode="after")
    @classmethod
    def _validate_models_after_(cls, values: dict[str, AQMModelConfig]) -> dict[str, AQMModelConfig]:
        is_host = set([k for k, v in values.items() if v.is_host])
        if len(is_host) != 1:
            raise ValueError(f"Only one model can be host. Found {is_host}.")
        return values


class Config(BaseModel):
    model_config = {"frozen": True}

    aqm: AQMConfig
    start_datetime: str = Field(description="Evaluation start time in yyyy-mm-dd-HH:MM:SS UTC format.")
    end_datetime: str = Field(description="Evaluation end time in yyyy-mm-dd-HH:MM:SS UTC format.")
    cartopy_data_dir: PathExistingDir = Field(description="Path to the Cartopy data directory.")
    output_dir: Path  # tdk:doc: existing directory
    run_dir: Path

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
        key = cls._key.default  # type: ignore[attr-defined]
        return cls.model_validate(data[key])

    @staticmethod
    def update_left(data_left: dict, data_right: dict) -> None:
        for key, value in data_right.items():
            # if key not in data_left:
            #     data_left[key] = value
            if isinstance(data_left.get(key), Mapping):
                Config.update_left(data_left[key], value)
            else:
                data_left[key] = value

    @model_validator(mode="after")
    def _validate_model_after_(self) -> "Config":
        _ = self.date_range
        return self
