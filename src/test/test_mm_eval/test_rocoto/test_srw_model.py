import yaml

from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.rocoto.srw_model import AqmPrep, AqmEvalTask, AqmTaskGroup


def test_task_group():
    data = {"nodes": "1", "walltime": "00:05:00", "envars_custom": {}, "package_key": PackageKey.CHEM, "nprocs": "10"}
    prep = AqmPrep.model_validate(data)

    data = {"nodes": "1", "walltime": "00:05:00", "package_key": PackageKey.CHEM, "task_key": TaskKey.SAVE_PAIRED, "nprocs": "10"}
    chem = AqmEvalTask.model_validate(data)

    data["task_key"] = TaskKey.BOXPLOT
    boxplot = AqmEvalTask.model_validate(data)

    tg = AqmTaskGroup(packages=(prep,), tasks=(chem, boxplot))
    print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))


def test_task_group_from_config(srw_context: SRWContext):
    tg = AqmTaskGroup.from_config(srw_context.mm_config)
    print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))