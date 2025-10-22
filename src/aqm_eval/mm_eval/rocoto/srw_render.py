from abc import ABC
from functools import cached_property
from pathlib import Path

import jinja2
from pydantic import BaseModel, computed_field

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey


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
    tasks: TaskDataCollection

    host: str = "task_mm_prep"

class PackageDataCollection(BaseModel):
    members: tuple[PackageData, ...]


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
        )
        return env.get_template(self.template_name)

    @computed_field
    @cached_property
    def out_path(self) -> Path:
        return self.out_dir / self.template_name.replace(".j2", "")

    def run(self) -> None:
        config_yaml = self.template.render(coll=self.coll)
        self.out_path.write_text(config_yaml)

