from typing import Any

from aqm_eval.base import AeBaseModel
from aqm_eval.mm_eval.driver.task.plot import PlotTask
from aqm_eval.mm_eval.driver.task.save_paired import Analysis
from aqm_eval.mm_eval.driver.task.stats import StatsTask


class Observations(AeBaseModel):
    filename: str
    variables: dict
    use_airnow: bool = True
    obs_type: str = "pt_sfc"


class MM_Model(AeBaseModel):
    files: str
    mod_type: str
    mod_kwargs: dict
    radius_of_influence: float
    mapping: dict[str, dict]
    plot_kwargs: dict[str, Any]
    variables: Any | None = None
    projection: Any | None = None


class TaskTemplate(AeBaseModel):
    analysis: Analysis
    model: dict[str, MM_Model]
    obs: dict[str, Observations]

    def to_yaml(self) -> dict:
        return self.model_dump(mode="json")


class PlotTasksTemplate(TaskTemplate):
    plots: dict[str, PlotTask]

    def to_yaml(self) -> dict:
        return self.model_dump(mode="json")


class StatsTaskTemplate(TaskTemplate):
    stats: StatsTask
