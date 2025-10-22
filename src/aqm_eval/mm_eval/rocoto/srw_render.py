from abc import ABC
from functools import cached_property
from pathlib import Path

import jinja2
from pydantic import BaseModel, computed_field

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey, package_key_to_class


class AbstractExecutionData(ABC, BaseModel):
    key: PackageKey | TaskKey
    host: str

    @cached_property
    def nodes(self) -> str:
        return "{{{{ {host}.{key}.nodes }}}}:ppn={{{{ {host}.{key}.tasks_per_node }}}}".format(
            key=self.key.value, host=self.host)

    @cached_property
    def nprocs(self) -> str:
        return "{{{{ {host}.{key}.nodes * {host}.{key}.tasks_per_node }}}}".format(
            key=self.key.value, host=self.host)

    @cached_property
    def walltime(self) -> str:
        return "{{{{ {host}.{key}.walltime }}}}".format(key=self.key.value, host=self.host)


class TaskData(AbstractExecutionData):
    key: TaskKey
    host: str = "task_mm_run"

class TaskDataCollection(BaseModel):
    members: tuple[TaskData, ...]

class PackageData(AbstractExecutionData):
    key: PackageKey

    host: str = "task_mm_prep"

    @computed_field
    @cached_property
    def tasks(self) -> TaskDataCollection:
        members = tuple([TaskData(key=ii) for ii in package_key_to_class(self.key).model_fields["tasks_default"].default])
        return TaskDataCollection(members=members)

class PackageDataCollection(BaseModel):

    @computed_field
    @cached_property
    def members(self) -> tuple[PackageData, ...]:
        return tuple([PackageData(key=ii) for ii in PackageKey])



class Renderer(BaseModel):
    coll: PackageDataCollection
    out_dir: Path
    template_name: str = "aqm_post_melodies_monet.yaml.j2"

    @cached_property
    def template(self) -> jinja2.Template:
        searchpath = Path(__file__).parent
        LOGGER(f"creating J2 environment {searchpath=}")
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=searchpath),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,

        )
        return env.get_template(self.template_name)

    @computed_field
    @cached_property
    def out_path(self) -> Path:
        return self.out_dir / self.template_name.replace(".j2", "")

    def run(self) -> None:
        config_yaml = self.template.render(coll=self.coll)
        self.out_path.write_text(config_yaml)

