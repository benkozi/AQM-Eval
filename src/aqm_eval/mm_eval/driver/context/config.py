from pathlib import Path
from typing import Any, Annotated

from pydantic import BaseModel, model_serializer, field_serializer, Field, BeforeValidator

from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey
from aqm_eval.shared import PathExisting


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

    key: PackageKey #tdk: is unique
    execution: Execution
    observation_template: str
    tasks: tuple[TaskKey, ...] #tdk: is unique, save_paired is always first and required



class AQMModelConfig(BaseModel):
    model_config = {"frozen": True}

    key: str #tdk: no spaces, - and _ only
    title: str #tdk: unique in coll
    path: PathExisting
    color: str #tdk: any valid matplotlib color, unique in coll
    is_host: bool = False # tdk: only one model needs to be host = true but must be one


class AQMConfig(BaseModel):
    model_config = {"frozen": True}

    output_dir: Path
    models: tuple[AQMModelConfig, ...] = Field(min_length=1)
    packages: tuple[PackageConfig, ...] = Field(min_length=1)
    packages_to_run: tuple[PackageKey, ...] = Field(min_length=1)


class Config(BaseModel):
    model_config = {"frozen": True}

    aqm: AQMConfig
    key: str = "melodies_monet_parm"

    def to_yaml_as_json(self) -> dict:
        ret = self.model_dump(mode="json")
        ret = {self.key: ret}
        return ret

    @classmethod
    def from_yaml_as_json(cls, data: dict) -> "Config":
        return cls.model_validate(data[cls.model_fields["key"].default])