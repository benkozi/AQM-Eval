"""Implements the Short-Range Weather (SRW) App driver context."""

import logging
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.mm_eval.driver.helpers import PathExisting
from aqm_eval.mm_eval.driver.package import AbstractEvalPackage, ChemEvalPackage, MetEvalPackage, PackageKey, TaskKey

try:
    from uwtools.api.config import YAMLConfig, get_yaml_config
except ImportError as exc:
    LOGGER("uwtools required for SRW context", exc_info=exc)


def _convert_date_string_to_mm_(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d%H")
    return dt.strftime("%Y-%m-%d-%H:00:00")


class SRWContext(AbstractDriverContext):
    expt_dir: PathExisting = Field(description="Experiment directory.")

    @computed_field
    @cached_property
    def config_path_user(self) -> PathExisting:
        return self.expt_dir / "config.yaml"

    @computed_field
    @cached_property
    def config_path_rocoto(self) -> PathExisting:
        return self.expt_dir / "rocoto_defns.yaml"

    @computed_field
    @cached_property
    def config_path_var_defns(self) -> PathExisting:
        return self.expt_dir / "var_defns.yaml"

    @computed_field
    @cached_property
    def date_first_cycle_srw(self) -> str:
        return self.find_nested_key(("workflow", "DATE_FIRST_CYCL"))

    @computed_field
    @cached_property
    def date_last_cycle_srw(self) -> str:
        return self.find_nested_key(("workflow", "DATE_LAST_CYCL"))

    @computed_field
    @cached_property
    def date_first_cycle_mm(self) -> str:
        return _convert_date_string_to_mm_(self.date_first_cycle_srw)

    @computed_field
    @cached_property
    def date_last_cycle_mm(self) -> str:
        return _convert_date_string_to_mm_(self.date_last_cycle_srw)

    @computed_field
    @cached_property
    def mm_output_dir(self) -> PathExisting:
        config_path = self.find_nested_key(("task_mm_prep", "MM_OUTPUT_DIR"))
        if config_path is None:
            config_path = self.expt_dir / "mm_output"
        if not config_path.exists():
            config_path.mkdir(exist_ok=True, parents=True)
        return config_path

    @computed_field
    @cached_property
    def mm_run_dir(self) -> PathExisting:
        ret = self.expt_dir / "mm_run"
        ret.mkdir(exist_ok=True, parents=True)
        return ret

    @computed_field
    @cached_property
    def mm_package_keys(self) -> tuple[PackageKey, ...]:
        return tuple([PackageKey(ii) for ii in self.find_nested_key(("task_mm_prep", "MM_EVAL_PACKAGES"))])

    @computed_field
    @cached_property
    def mm_obs_airnow_fn_template(self) -> str:
        return self.find_nested_key(("task_mm_prep", "MM_OBS_AIRNOW_FN_TEMPLATE"))

    @computed_field
    @cached_property
    def mm_obs_ish_fn_template(self) -> str:  # tdk:last: ish or met?
        return self.find_nested_key(("task_mm_prep", "MM_OBS_ISH_FN_TEMPLATE"))

    @computed_field
    @cached_property
    def link_simulation(self) -> tuple[str, ...]:
        return tuple(set([f"{str(ii.year)}*" for ii in [self.datetime_first_cycl, self.datetime_last_cycl]]))

    @computed_field
    @cached_property
    def link_alldays_path(self) -> PathExisting:
        ret = self.mm_run_dir / "Alldays"
        ret.mkdir(exist_ok=True, parents=True)
        return ret

    @computed_field
    @cached_property
    def mm_base_model_expt_dir(self) -> PathExisting | None:
        return self.find_nested_key(("task_mm_prep", "MM_BASE_MODEL_EXPT_DIR"))

    @computed_field
    @cached_property
    def cartopy_data_dir(self) -> PathExisting:
        return PathExisting(self.find_nested_key(("platform", "FIXshp"))).absolute().resolve(strict=True)

    @cached_property
    def mm_packages(self) -> tuple[AbstractEvalPackage, ...]:
        ret: list[AbstractEvalPackage] = []
        mapping = {PackageKey.CHEM: ChemEvalPackage, PackageKey.MET: MetEvalPackage}
        for package_key in self.mm_package_keys:
            # tdk:last: replace with dedicated function in package.py
            ret.append(
                mapping[package_key](
                    root_dir=self.mm_run_dir,
                    mm_eval_model_expt_dir=self.expt_dir,
                    link_simulation=self.link_simulation,
                    link_alldays_path=self.link_alldays_path,
                    mm_base_model_expt_dir=self.mm_base_model_expt_dir,
                )
            )
        return tuple(ret)

    @cached_property
    def datetime_first_cycl(self) -> datetime:
        return datetime.strptime(self.date_first_cycle_srw, "%Y%m%d%H")

    @cached_property
    def datetime_last_cycl(self) -> datetime:
        return datetime.strptime(self.date_last_cycle_srw, "%Y%m%d%H")

    @cached_property
    def yaml_data(self) -> dict[Path, YAMLConfig]:
        """Cache loaded YAML data from config files."""
        data = {}
        for yaml_path in self.yaml_srw_config_paths:
            data[yaml_path] = get_yaml_config(yaml_path)
        return data

    @cached_property
    def yaml_srw_config_paths(self) -> tuple[PathExisting, ...]:
        return self.config_path_user, self.config_path_rocoto, self.config_path_var_defns

    def find_nested_key(self, key_tuple: tuple[str, ...]) -> Any:
        """Find a nested key in the YAML dictionaries using a tuple of string keys.

        Args:
            key_tuple: Tuple of strings representing nested dictionary keys

        Returns
        -------
            The value found at the nested key location
        """
        for yaml_path, yaml_dict in self.yaml_data.items():
            current = yaml_dict
            try:
                for key in key_tuple:
                    current = current[key]
                return current
            except KeyError:
                continue
            except:
                LOGGER(
                    f"unexpected error: {key_tuple=}, {type(current)=}",
                    level=logging.ERROR,
                )
                raise
        raise KeyError(f"{key_tuple=} not found in any YAML files: {self.yaml_data.keys()}")

    def create_control_configs(self) -> None:
        for package in self.mm_packages:
            package_run_dir = package.run_dir
            LOGGER(f"{package_run_dir=}")
            if not package_run_dir.exists():
                LOGGER(f"{package_run_dir=} does not exist. creating.")
                package_run_dir.mkdir(exist_ok=True, parents=True)

            cfg = {"ctx": self, "mm_tasks": tuple([ii.value for ii in package.tasks]), "package": package}
            namelist_config_str = self.j2_env.get_template(package.namelist_template).render(cfg)
            namelist_config = yaml.safe_load(namelist_config_str)
            with open(package_run_dir / "namelist.yaml", "w") as f:
                f.write(namelist_config_str)

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
