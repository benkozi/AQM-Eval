from copy import deepcopy
from functools import cached_property
from pathlib import Path
from typing import Any, Annotated, Mapping

from pydantic import BaseModel, model_serializer, field_serializer, Field, BeforeValidator, \
    field_validator, AfterValidator

from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey
from aqm_eval.shared import PathExisting, PathExistingDir


def _is_unique_(v: tuple[Any, ...]) -> tuple[Any, ...]:
    if len(set(v)) != len(v):
        raise ValueError(f"Values must be unique.")
    return v


class BatchArgs(BaseModel):
    model_config = {"frozen": True}

    nodes: int = Field(ge=1)
    tasks_per_node: int = Field(ge=1)
    walltime: str #tdk: format is HH:MM:SS


class Execution(BaseModel):
    model_config = {"frozen": True}

    batchargs: BatchArgs


class PackageConfig(BaseModel):
    model_config = {"frozen": True}

    active: bool
    observation_template: str
    tasks: tuple[TaskKey, ...] #tdk: is unique, save_paired is always first and required
    execution: Execution



class AQMModelConfig(BaseModel):
    model_config = {"frozen": True}

    title: str #tdk: unique in coll
    expt_dir: PathExistingDir
    color: str #tdk: any valid matplotlib color, unique in coll
    is_host: bool = False # tdk: only one model needs to be host = true but must be one



def _validate_models_(value: dict[str, AQMModelConfig]) -> dict[str, AQMModelConfig]:
    is_host = set([k for k, v in value.items() if v.is_host])
    if len(is_host) != 1:
        raise ValueError(f"Only one model can be host. Found {is_host}.")
    return value


class AQMConfig(BaseModel):
    model_config = {"frozen": True}

    output_dir: Path #tdk:doc: existing directory
    models: Annotated[dict[str, AQMModelConfig], AfterValidator(_validate_models_)] #tdk: str key is unique
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