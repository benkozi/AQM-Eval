from pathlib import Path
from typing import Any, Annotated

from pydantic import BaseModel, model_serializer, field_serializer, Field, BeforeValidator

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

    key: str
    title: str #tdk: unique in coll
    expt_dir: PathExistingDir
    color: str #tdk: any valid matplotlib color, unique in coll
    is_host: bool = False # tdk: only one model needs to be host = true but must be one


class AQMConfig(BaseModel):
    model_config = {"frozen": True}

    output_dir: Path #tdk:doc: existing directory
    models: dict[str, AQMModelConfig] #tdk: str key is unique
    packages: dict[PackageKey, PackageConfig] = Field(min_length=1)


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