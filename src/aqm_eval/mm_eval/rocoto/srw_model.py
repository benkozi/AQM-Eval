from abc import ABC
from pathlib import Path

from pydantic import BaseModel, Field, computed_field, model_validator

from aqm_eval.mm_eval.driver.config import Config, PackageKey, TaskKey
from aqm_eval.mm_eval.driver.package.core import package_key_to_class


class AbstractAqmTask(ABC, BaseModel):
    model_config = {"frozen": True}

    node_count: str = Field(exclude=True)
    walltime: str
    command: str
    nprocs: str = Field(exclude=True)

    account: str = "&ACCOUNT;"
    attrs: dict = {"cycledefs": "at_end", "maxtries": "1"}
    native: str = "{{ platform.SCHED_NATIVE_CMD }}"
    partition: str = '{{ "&PARTITION_DEFAULT;" if platform.get("PARTITION_DEFAULT") }}'
    queue: str = "&QUEUE_DEFAULT;"
    join: dict = {"cyclestr": {"value": "&LOGDIR;/{{ jobname }}_@Y@m@d@H&LOGEXT;"}}

    _envars_default: dict = {
        "GLOBAL_VAR_DEFNS_FP": "&GLOBAL_VAR_DEFNS_FP;",
        "HOMEdir": "&HOMEdir;",
        "LOGDIR": {"cyclestr": {"value": "&LOGDIR;"}},
    }

    @computed_field
    def envars(self) -> dict:
        raise NotImplementedError

    @computed_field
    def task_name(self) -> str:
        raise NotImplementedError

    @computed_field
    def dependency(self) -> dict:
        raise NotImplementedError

    @computed_field
    def nodes(self) -> str:
        return f"{self.node_count}:ppn={self.nprocs}"

    def to_yaml(self) -> dict:
        data = self.model_dump(mode="json", exclude={"task_name"})
        ret = {self.task_name: data}
        return ret

    @model_validator(mode="after")
    def _validate_(self) -> "AbstractAqmTask":
        _ = self.model_dump()
        return self


class AqmPrep(AbstractAqmTask):
    package_key: PackageKey = Field(exclude=True)
    command: str = '&LOAD_MODULES_RUN_TASK; "mm_prep" "&HOMEdir;/jobs/JSRW_AQM_MELODIES_MONET_PREP"'

    @computed_field
    def dependency(self) -> dict:
        return {
            "and": {
                "or": {
                    "not": {"taskvalid": {"attrs": {"task": "run_fcst_mem000"}}},
                    "and": {"taskvalid": {"attrs": {"task": "run_fcst_mem000"}}, "taskdep": {"attrs": {"task": "run_fcst_mem000"}}},
                }
            }
        }

    @computed_field
    def envars(self) -> dict:
        return self._envars_default | {
            # "nprocs": self.nprocs,
            "MM_EVAL_PACKAGE": self.package_key.value
        }

    @computed_field
    def task_name(self) -> str:
        return f"task_mm_{self.package_key.value}_prep"


class AqmEvalTask(AbstractAqmTask):
    package_key: PackageKey = Field(exclude=True)
    task_key: TaskKey = Field(exclude=True)

    command: str = '&LOAD_MODULES_RUN_TASK; "mm_run" "&HOMEdir;/jobs/JSRW_AQM_MELODIES_MONET_RUN"'

    @computed_field
    def dependency(self) -> dict:
        match self.task_key:
            case TaskKey.SAVE_PAIRED:
                task_dep = f"mm_{self.package_key.value}_prep"
            case _:
                task_dep = f"mm_{self.package_key.value}_run_save_paired"
        return {"and": {"taskdep": {"attrs": {"task": task_dep}}}}

    @computed_field
    def envars(self) -> dict:
        return self._envars_default | {
            # "nprocs": self.nprocs,
            "MM_EVAL_PACKAGE": self.package_key.value,
            "MM_EVAL_TASK": self.task_key.value,
        }

    @computed_field
    def task_name(self) -> str:
        return f"task_mm_{self.package_key.value}_run_{self.task_key.value}"


class AqmConcatStatsTask(AbstractAqmTask):
    active_package_keys: tuple[PackageKey, ...] = Field(exclude=True)
    output_dir: Path = Field(exclude=True)
    node_count: str = Field(default="1", exclude=True)
    walltime: str = "00:05:00"
    nprocs: str = Field(default="1", exclude=True)
    command: str = '&LOAD_MODULES_RUN_TASK; "mm_concat_stats" "&HOMEdir;/jobs/JSRW_AQM_MELODIES_MONET_CONCAT_STATS"'

    @computed_field
    def envars(self) -> dict:
        return self._envars_default | {"MM_OUTPUT_DIR": str(self.output_dir)}

    @computed_field
    def task_name(self) -> str:
        return "task_mm_concat_stats"

    @computed_field
    def dependency(self) -> dict:
        ret = {}
        for package_key in self.active_package_keys:
            ret[f"taskdep_{package_key.value}"] = {"attrs": {"task": f"mm_{package_key.value}_run_{TaskKey.STATS.value}"}}
        return {"and": ret}


class AqmTaskGroup(BaseModel):
    packages: tuple[AqmPrep, ...]
    tasks: tuple[AqmEvalTask, ...]
    concat_task: AqmConcatStatsTask

    def to_yaml(self) -> dict:
        ret = {}
        for ii in self.packages:
            ret.update(ii.to_yaml())
        for jj in self.tasks:
            ret.update(jj.to_yaml())
        if len(self.concat_task.active_package_keys) >= 1:
            ret.update(self.concat_task.to_yaml())
        return ret

    @classmethod
    def from_config(cls, config: Config) -> "AqmTaskGroup":
        packages = []
        tasks = []
        active_package_keys = []
        for package in config.aqm.packages.values():
            if package.active:
                package_batchargs = package.execution.prep.batchargs
                data = {
                    "node_count": str(package_batchargs.nodes),
                    "walltime": package_batchargs.walltime,
                    "package_key": package.key,
                    "nprocs": str(package_batchargs.tasks_per_node),
                }
                packages.append(AqmPrep.model_validate(data))
                package_class = package_key_to_class(package.key)
                for task_key in package_class.model_fields["tasks_default"].default:
                    if config.aqm.n_models_to_evaluate == 1 and task_key.value.startswith("scorecard"):
                        continue
                    if task_key not in package.tasks_to_exclude:
                        if task_key == TaskKey.STATS:
                            active_package_keys.append(package.key)
                        task_batchargs = package.execution.tasks.get(task_key, config.aqm.task_defaults.execution).batchargs
                        data = {
                            "node_count": str(task_batchargs.nodes),
                            "walltime": task_batchargs.walltime,
                            "package_key": package.key,
                            "task_key": task_key,
                            "nprocs": str(task_batchargs.tasks_per_node),
                        }
                        tasks.append(AqmEvalTask.model_validate(data))
        return AqmTaskGroup(
            packages=tuple(packages),
            tasks=tuple(tasks),
            concat_task=AqmConcatStatsTask(active_package_keys=tuple(active_package_keys), output_dir=config.output_dir),
        )
