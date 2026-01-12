from aqm_eval.base import AeBaseModel
from aqm_eval.mm_eval.driver.config import ScorecardMethod


class ScorecardTask(AeBaseModel):
    key: str
    better_or_worse_method: ScorecardMethod
    data: list[str]
    model_name_list: list[str]

    type: str = "scorecard"
    fig_kwargs: dict = {"figsize": [18, 10]}
    text_kwargs: dict = {"fontsize": 24}
    domain_type: list[str] = ["all"]
    domain_name: list[str] = ["CONUS"]
    region_name: list[str] = ["epa_region"]
    region_list: list[str] = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"]
    urban_rural_name: list[str] = ["msa_name"]
    urban_rural_differentiate_value: str = ""
    data_proc: dict = {
        "rem_obs_nan": True,  # True: Remove all points where model or obs is NaN; False: Remove only points where model is NaN.
        "set_axis": False,  # If True, add `vmin_plot` and `vmax_plot` for each variable in obs.
    }

    def to_yaml(self) -> dict:
        data = self.model_dump(mode="json", exclude={"key"})
        prefix = f"{self.better_or_worse_method.get_mm_prefix()}_{self.key}"
        return {"plots": {prefix: data}}
