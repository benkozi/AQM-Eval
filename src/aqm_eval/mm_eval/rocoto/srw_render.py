from abc import ABC
from functools import cached_property
from pathlib import Path

import jinja2
from pydantic import BaseModel, computed_field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey, package_key_to_class


class AbstractExecutionData(ABC, BaseModel):
    key: PackageKey | TaskKey
    host: str

    @cached_property
    def execution_host(self) -> str:
        return f"{self.host}.{self.key.value}.execution.batchargs"

    @cached_property
    def nodes(self) -> str:
        return "{{{{ {host}.nodes }}}}:ppn={{{{ {host}.tasks_per_node }}}}".format(host=self.execution_host)

    @cached_property
    def nprocs(self) -> str:
        return "{{{{ {host}.nodes * {host}.tasks_per_node }}}}".format(host=self.execution_host)

    @cached_property
    def walltime(self) -> str:
        return "{{{{ {host}.walltime }}}}".format(host=self.execution_host)


class TaskData(AbstractExecutionData):
    key: TaskKey
    host: str = "melodies_monet_parm.aqm.tasks"

    @cached_property
    def execution_host(self) -> str:
        return f"{self.host}.execution.batchargs"


class TaskDataCollection(BaseModel):
    members: tuple[TaskData, ...]


class PackageData(AbstractExecutionData):
    key: PackageKey

    host: str = "melodies_monet_parm.aqm.packages"

    @computed_field
    @cached_property
    def tasks(self) -> TaskDataCollection:
        members = tuple([TaskData(key=ii) for ii in package_key_to_class(self.key).model_fields["tasks_default"].default])
        return TaskDataCollection(members=members)

    @cached_property
    def should_run(self) -> str:
        path = f"{self.host}.packages_to_run"
        ret = '{{% if "{key}" in {path} %}}run_package{{% endif %}}'.format(key=self.key.value, path=path)
        return ret

    @cached_property
    def should_run_task(self) -> dict[TaskKey, str]:
        ret = {}
        for ii in self.tasks.members:
            tasks_to_exclude = f"{self.host}.{self.key.value}.tasks_to_exclude"
            should_run = '{{% if "{task_key}" not in {tasks_to_exclude} %}}run_task{{% endif %}}'.format(
                task_key=ii.key.value, tasks_to_exclude=tasks_to_exclude
            )
            ret[ii.key] = should_run
        return ret


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
            # trim_blocks=True,
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


@log_it
def render_task_group(tmp_path: Path) -> None:
    packages = PackageDataCollection()
    LOGGER(str(packages))
    renderer = Renderer(coll=packages, out_dir=tmp_path)
    LOGGER(str(renderer))
    renderer.run()
    LOGGER(renderer.out_path.read_text())
