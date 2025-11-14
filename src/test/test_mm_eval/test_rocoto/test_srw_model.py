import yaml

from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.rocoto.srw_model import AqmEvalTask, AqmPrep, AqmTaskGroup


def test_task_group() -> None:
    data = {"node_count": "1", "walltime": "00:05:00", "package_key": PackageKey.CHEM, "nprocs": "10"}
    prep = AqmPrep.model_validate(data)

    data["task_key"] = TaskKey.SAVE_PAIRED
    chem = AqmEvalTask.model_validate(data)

    data["task_key"] = TaskKey.BOXPLOT
    boxplot = AqmEvalTask.model_validate(data)

    tg = AqmTaskGroup(packages=(prep,), tasks=(chem, boxplot))
    print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))


def test_task_group_from_config(srw_context: SRWContext) -> None:
    mm_config = srw_context.mm_config
    assert mm_config.active is True
    tg = AqmTaskGroup.from_config(mm_config)
    print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))
