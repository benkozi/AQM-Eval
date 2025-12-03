from pathlib import Path

import yaml

from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.rocoto.srw_model import AqmConcatStatsTask, AqmEvalTask, AqmPrep, AqmTaskGroup


def test_task_group(tmp_path: Path) -> None:
    data = {"node_count": "1", "walltime": "00:05:00", "package_key": PackageKey.CHEM, "nprocs": "10"}
    prep = AqmPrep.model_validate(data)

    data["task_key"] = TaskKey.SAVE_PAIRED
    data["task_label"] = TaskKey.SAVE_PAIRED.value
    chem = AqmEvalTask.model_validate(data)

    data["task_key"] = TaskKey.BOXPLOT
    boxplot = AqmEvalTask.model_validate(data)

    concat = AqmConcatStatsTask.model_validate({"active_package_keys": tuple(PackageKey), "output_dir": tmp_path})
    # print(yaml.safe_dump(concat.to_yaml(), sort_keys=False))

    tg = AqmTaskGroup(packages=(prep,), tasks=(chem, boxplot), concat_task=concat)
    print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))


def test_task_group_from_config(srw_context: SRWContext) -> None:
    mm_config = srw_context.mm_config
    assert mm_config.aqm.active is True
    tg = AqmTaskGroup.from_config(mm_config)
    print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))


# tdk:rm
# def test_task_group_from_config_respects_defaults_tasks_per_node(srw_context: SRWContext) -> None:
#     # mm_config = srw_context.mm_config
#     config_data = Box(srw_context.mm_config.model_dump(), default_box=True)
#     # actual_data
#     # tasks = actual_data["aqm"]["packages"][PackageKey.CHEM]["execution"]["tasks"]
#     # tasks.setdefault(TaskKey.SAVE_PAIRED, {}).setdefault("batchargs", {})
#     # tasks[TaskKey.SAVE_PAIRED]["batchargs"] = {}
#     # tasks[TaskKey.SAVE_PAIRED]["batchargs"]["nprocs"] = 9999
#     # expected_value = 99999
#     config_data["aqm"]["packages"][PackageKey.CHEM]["execution"]["tasks"][TaskKey.SPATIAL_OVERLAY]["batchargs"]["nodes"] = 2
#     mm_config = Config.model_validate(config_data)
#     tg = AqmTaskGroup.from_config(mm_config)
#     actual = Box(tg.to_yaml())
#     print(yaml.safe_dump(tg.to_yaml(), sort_keys=False))
