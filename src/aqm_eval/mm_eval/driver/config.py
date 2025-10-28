from enum import unique, StrEnum
from functools import cached_property
from pathlib import Path
from typing import Any, Annotated, Mapping

from pydantic import BaseModel, Field, AfterValidator, model_validator

from aqm_eval.shared import PathExistingDir


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
        raise ValueError(f"Values must be unique.")
    return v


class BatchArgs(BaseModel):
    model_config = {"frozen": True}

    nodes: int = Field(ge=1)
    tasks_per_node: int = Field(ge=1)
    walltime: str  # tdk: format is HH:MM:SS


class Execution(BaseModel):
    model_config = {"frozen": True}

    batchargs: BatchArgs


class PackageConfig(BaseModel):
    model_config = {"frozen": True}

    key: PackageKey  # tdk: this should not be written out and should automatically be populated
    active: bool
    observation_template: str
    tasks_to_exclude: tuple[
        TaskKey, ...]  # tdk: is unique, save_paired is always first and required
    execution: Execution
    mapping: dict[str, str]

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

    color: str = "forestgreen"  # tdk: this needs to be auto-generated and unique
    marker: str = '^'
    linestyle: str = '-'
    markersize: int = 4


class AQMModelConfig(BaseModel):
    model_config = {"frozen": True}

    title: str  # tdk: unique in coll
    expt_dir: PathExistingDir
    plot_kwargs: PlotKwargs
    is_host: bool = False  # tdk: only one model needs to be host = true but must be one
    type: str = "rrfs"
    kwargs: dict[str, Any] = {'surf_only': True, 'mech': 'cb6r3_ae6_aq'}
    radius_of_influence: float = 20000
    variables: Any | None = None
    projection: Any | None = None


def _validate_models_after_(value: dict[str, AQMModelConfig]) -> dict[str, AQMModelConfig]:
    is_host = set([k for k, v in value.items() if v.is_host])
    if len(is_host) != 1:
        raise ValueError(f"Only one model can be host. Found {is_host}.")
    return value


class AQMConfig(BaseModel):
    model_config = {"frozen": True}

    output_dir: Path  # tdk:doc: existing directory
    models: Annotated[dict[str, AQMModelConfig], AfterValidator(_validate_models_after_)] = Field(
        max_length=4)
    packages: dict[PackageKey, PackageConfig] = Field(min_length=1)

    @cached_property
    def host_model(self) -> dict[str, AQMModelConfig]:
        for k, v in self.models.items():
            if v.is_host:
                return {k: v}
        raise ValueError("No host model found.")


class Config(BaseModel):
    model_config = {"frozen": True}

    aqm: AQMConfig

    _key: str = "melodies_monet_parm"

    def to_yaml(self) -> dict:
        ret = self.model_dump(mode="json")
        ret = {self._key: ret}
        return ret

    @classmethod
    def from_yaml(cls, data: dict) -> "Config":
        return cls.model_validate(data[cls._key.default])

    @classmethod
    def from_yaml_overlay(cls, data_left: dict, data_right: dict) -> "Config":
        data_left = cls._update_left_(data_left[cls._key.default], data_right[cls._key.default])
        return cls.from_yaml({cls._key.default: data_left})

    @staticmethod
    def _update_left_(data_left: dict, data_right: dict) -> dict:
        for key, value in data_right.items():
            if isinstance(data_left[key], Mapping):
                Config._update_left_(data_left[key], value)
            else:
                data_left[key] = value
        return data_left
