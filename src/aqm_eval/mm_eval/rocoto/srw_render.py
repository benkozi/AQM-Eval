from functools import cached_property
from pathlib import Path

import jinja2
from pydantic import BaseModel, computed_field

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey


class PackageData(BaseModel):
    key: PackageKey
    tasks: tuple[TaskKey, ...]

    @cached_property
    def nodes(self) -> str:
        return "{{{{ task_mm_prep.{key}.nodes }}}}:ppn={{{{ task_mm_prep.{key}.tasks_per_node }}}}".format(key=self.key.value)

    @cached_property
    def nprocs(self) -> str:
        return "{{{{ task_mm_prep.{key}.nodes * task_mm_prep.{key}.tasks_per_node }}}}".format(key=self.key.value)

    @cached_property
    def walltime(self) -> str:
        return "{{{{ task_mm_prep.{key}.walltime }}}}".format(key=self.key.value)

class PackageDataCollection(BaseModel):
    packages: tuple[PackageData, ...]


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

