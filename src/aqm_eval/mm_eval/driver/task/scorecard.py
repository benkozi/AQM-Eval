from functools import cached_property

from pydantic import BaseModel

from aqm_eval.mm_eval.driver.config import ScorecardMethod, ScorecardConfig
from aqm_eval.mm_eval.driver.model import Model


class ScorecardTask(BaseModel):
    model_config = {"frozen": True} #tdk: replace BaseModel with AQM_Eval_BaseModel

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

    # @classmethod
    # def write_mm_configs(cls, scorecards: ScorecardConfig, mm_models: tuple[Model, ...]) -> None:
    #     for scorecard_cfg in scorecards.values():
    #         for scorecard_method in ScorecardMethod:
    #             scorecard_data = [scorecard_cfg.sensitivity, scorecard_cfg.control]
    #             scorecard_models = []
    #             for ii in scorecard_data:
    #                 for jj in mm_models:
    #                     if jj.label == ii:
    #                         scorecard_models.append(jj)
    #                         break
    #             if len(scorecard_models) != len(scorecard_data):
    #                 raise ValueError(f"could not find all models for scorecard {scorecard_cfg.key=}")
    #             scorecard_task = ScorecardTask(key=scorecard_cfg.key,
    #                                            better_or_worse_method=scorecard_method,
    #                                            data=scorecard_data,
    #                                            model_name_list=[self.observations_title] + [ii.label for ii in scorecard_models])
    #             plot_yaml = scorecard_task.to_yaml()
    #             plot_yaml_str = yaml.safe_dump(plot_yaml)
    #             config_yaml = template.render({**namelist_config, **{"plot_yaml_str": plot_yaml_str}})
    #             curr_control_path = package_run_dir / f"control_scorecard_{scorecard_method.value}_{scorecard_key}.yaml"
    #             LOGGER(f"{curr_control_path=}")
    #             curr_control_path.write_text(config_yaml)