from aqm_eval.base import AeBaseModel
from aqm_eval.mm_eval.driver.config import TaskKey


class PlotTask(AeBaseModel):
    type: TaskKey
    fig_kwargs: dict
    default_plot_kwargs: dict
    text_kwargs: dict
    domain_type: list[str]
    domain_name: list[str]
    data: list[str]
    data_proc: dict
    model_name_list: list[str]

    score_name: str | None = None
    threshold_list: list[float] | None = None
    region_name: list[str] | None = None
    region_list: list[str] | None = None
    urban_rural_name: list[str] | None = None
    urban_rural_differentiate_value: str | None = None
    better_or_worse_method: str | None = None
