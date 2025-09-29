"""Implements the pure YAML driver context for MM evaluation packages."""

from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.mm_eval.driver.helpers import PathExisting
from aqm_eval.mm_eval.driver.model import Model, ModelRole
from aqm_eval.mm_eval.driver.package import AbstractEvalPackage, ChemEvalPackage, TaskKey


def _get_or_create_path_(path: str | Path) -> PathExisting:
    path = Path(path)
    if not path.exists():
        path.mkdir(exist_ok=True, parents=True)
    return PathExisting(path)


class YAMLContext(AbstractDriverContext):
    model_config = {"frozen": True}

    yaml_config: PathExisting = Field(description="Path to the YAML configuration file for the MM package.")

    @computed_field
    @cached_property
    def date_first_cycle_mm(self) -> str:
        return self._config_data["start_time"]

    @computed_field
    @cached_property
    def date_last_cycle_mm(self) -> str:
        return self._config_data["end_time"]

    @computed_field
    @cached_property
    def cartopy_data_dir(self) -> PathExisting:
        return PathExisting(self._config_data["cartopy_data_dir"])

    @cached_property
    def mm_packages(self) -> tuple[AbstractEvalPackage, ...]:
        # tdk: these need to be pulled from the yaml file. new entry?
        return (
            ChemEvalPackage(
                root_dir=self.mm_output_dir,
                use_base_model=True,
            ),
        )

    @computed_field
    @cached_property
    def link_alldays_path(self) -> PathExisting:
        return _get_or_create_path_(self._config_data["link_Alldays_path"])

    @cached_property
    def mm_models(self) -> tuple[Model, ...]:
        data = self._config_data
        base_model = Model(
            expt_dir=Path(data["link_base_path"]),
            role=ModelRole.BASE,
            label=data["model_base_label"],
            title="Base AQM",
            prefix=data["link_base_predix"],
            cycle_dir_template=(data["link_simulation"],),
            dyn_file_template=(data["link_base_target"],),
            link_alldays_path=self.link_alldays_path,
        )
        eval_model = Model(
            expt_dir=Path(data["link_eval_path"]),
            role=ModelRole.BASE,
            label=data["model_eval_label"],
            title="Eval AQM",
            prefix=data["link_eval_predix"],
            cycle_dir_template=(data["link_simulation"],),
            dyn_file_template=(data["link_eval_target"],),
            link_alldays_path=self.link_alldays_path,
        )
        return eval_model, base_model

    @computed_field
    @cached_property
    def mm_run_dir(self) -> PathExisting:
        return _get_or_create_path_(self._config_data["run_dir"])

    @computed_field
    @cached_property
    def mm_obs_airnow_fn_template(self) -> str:
        return self._config_data["obs_file"]

    @computed_field
    @cached_property
    def mm_output_dir(self) -> PathExisting:
        return _get_or_create_path_(self._config_data["output_dir"])

    @computed_field
    @cached_property
    def template_dir(self) -> PathExisting:
        return (Path(__file__).parent.parent.parent / "yaml_template").absolute().resolve()

    @computed_field
    @cached_property
    def conda_bin(self) -> Path:
        return Path(self._config_data["conda_bin"])

    @cached_property
    def _config_data(self) -> dict[str, Any]:
        with open(self.yaml_config, "r") as f:
            return yaml.safe_load(f)

    def create_control_configs(self) -> None:
        for package in self.mm_packages:
            package_run_dir = package.run_dir
            LOGGER(f"{package_run_dir=}")
            if not package_run_dir.exists():
                LOGGER(f"{package_run_dir=} does not exist. creating.")
                package_run_dir.mkdir(exist_ok=True, parents=True)

            cfg = {"ctx": self, "mm_tasks": tuple([TaskKey(ii) for ii in self._config_data["mm_tasks"]])}
            with open(self.yaml_config, "r") as f:
                namelist_config = yaml.safe_load(f)

            assert isinstance(cfg["mm_tasks"], tuple)
            for task in cfg["mm_tasks"]:
                match task:
                    case TaskKey.SCORECARD_RMSE:
                        namelist_config["scorecard_eval_method"] = '"RMSE"'
                    case TaskKey.SCORECARD_IOA:
                        namelist_config["scorecard_eval_method"] = '"IOA"'
                    case TaskKey.SCORECARD_NMB:
                        namelist_config["scorecard_eval_method"] = '"NMB"'
                    case TaskKey.SCORECARD_NME:
                        namelist_config["scorecard_eval_method"] = '"NME"'

                LOGGER(f"{task=}")
                template = self.j2_env.get_template(f"template_{task}.j2")
                LOGGER(f"{template=}")
                config_yaml = template.render(**namelist_config)
                curr_control_path = package_run_dir / f"control_{task}.yaml"
                LOGGER(f"{curr_control_path=}")
                with open(curr_control_path, "w") as f:
                    f.write(config_yaml)

        run_script = self.j2_env.get_template("run_monet-gaeac6.sh.j2").render(
            {
                "mm_run_dir": self.mm_run_dir,
                "conda_bin": str(self.conda_bin),
                "yaml_config": str(self.yaml_config),
                "package_run_dir": str(package_run_dir),
            }
        )
        LOGGER(f"{run_script=}")
        with open(self.mm_run_dir / "run_monet.sh", "w") as f:
            f.write(run_script)
