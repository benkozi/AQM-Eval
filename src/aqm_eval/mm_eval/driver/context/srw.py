"""Implements the Short-Range Weather (SRW) App driver context."""

import logging
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, computed_field, BaseModel
from uwtools.api.config import YAMLConfig, get_yaml_config

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.config import Config, PlatformKey
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.settings import SETTINGS
from aqm_eval.shared import PathExisting, assert_directory_exists, assert_file_exists, update_left

#tdk: remove uwtools dependency

def _convert_date_string_to_mm_(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d%H")
    return dt.strftime("%Y-%m-%d-%H:00:00")


class SrwWorkflow(BaseModel):
    model_config = {"frozen": True}

    EXPT_BASEDIR: Path
    EXPT_SUBDIR: str
    DATE_FIRST_CYCL: str
    DATE_LAST_CYCL_MM: str


class SrwPlatform(BaseModel):
    model_config = {"frozen": True}

    FIXshp: Path


class SrwUser(BaseModel):
    model_config = {"frozen": True}

    MACHINE: str


class SRWContext(AbstractDriverContext):
    # expt_dir: PathExisting = Field(description="Experiment directory.")
    # default_config["workflow"]["EXPT_BASEDIR"]
    # default_config["workflow"]["EXPT_SUBDIR"]
    # default_config["platform"]["FIXshp"]
    # default_config["workflow"]["DATE_LAST_CYCL_MM"]
    # default_config["workflow"]["DATE_FIRST_CYCL"]

    workflow: SrwWorkflow
    platform: SrwPlatform
    user: SrwUser
    melodies_monet_parm: dict

    @computed_field
    @cached_property
    def expt_dir(self) -> Path:
        return self.workflow.EXPT_BASEDIR / self.workflow.EXPT_SUBDIR

    @classmethod
    def from_expt_dir(cls, path: Path) -> "SRWContext":
        path = path / "var_defns.yaml"
        data = get_yaml_config(path)["__mm_runtime__"]
        return cls.model_validate(data)

    # @computed_field
    # @cached_property
    # def config_path_user(self) -> PathExisting:
    #     return assert_file_exists(self.expt_dir / "config.yaml")
    #
    # @computed_field
    # @cached_property
    # def config_path_rocoto(self) -> PathExisting:
    #     return assert_file_exists(self.expt_dir / "rocoto_defns.yaml")
    #
    # @computed_field
    # @cached_property
    # def _config_path_var_defns(self) -> Path:
    #     return assert_file_exists(self.expt_dir / "var_defns.yaml")

    # @computed_field
    @cached_property
    def _date_first_cycle_srw(self) -> str:
        # return self._find_nested_key_(("workflow", "DATE_FIRST_CYCL"))
        return self.workflow.DATE_FIRST_CYCL

    # @computed_field
    @cached_property
    def _date_last_cycle_srw(self) -> str:
        # return self._find_nested_key_(("workflow", "DATE_LAST_CYCL_MM"))
        return self.workflow.DATE_LAST_CYCL_MM

    # @computed_field
    @cached_property
    def _date_first_cycle_mm(self) -> str:
        return _convert_date_string_to_mm_(self._date_first_cycle_srw)

    # @computed_field
    @cached_property
    def _date_last_cycle_mm(self) -> str:
        return _convert_date_string_to_mm_(self._date_last_cycle_srw)

    @cached_property
    def _mm_output_dir_default(self) -> Path:
        return self.expt_dir / "mm_output"

    @cached_property
    def _cartopy_data_dir(self) -> Path:
        # targte_dir = self._find_nested_key_(("platform", "FIXshp"))
        target_dir = self.platform.FIXshp
        return assert_directory_exists(target_dir).absolute().resolve(strict=True)

    @cached_property
    def mm_config(self) -> Config:
        # mm_parm_left = self._yaml_data[self.config_path_var_defns]["melodies_monet_parm"]

        raw = (SETTINGS.eval_template_dir / "config-default.yaml").read_text()
        mm_parm_left = yaml.safe_load(raw)["melodies_monet_parm"]
        mm_parm_right = self.melodies_monet_parm
        update_left(mm_parm_left, mm_parm_right)
        mm_parm = {
            "melodies_monet_parm": mm_parm_left,
        }

        root = mm_parm["melodies_monet_parm"]
        root_aqm = root["aqm"]

        found_host = False
        for k, v in root_aqm["models"].items():
            if v.get("is_host", False):
                v["expt_dir"] = self.expt_dir
                found_host = True
        if not found_host:
            raise ValueError("No host model found.")

        if root.get("output_dir") is None:
            root["output_dir"] = self._mm_output_dir_default
        if root.get("run_dir") is None:
            root["run_dir"] = self.expt_dir / "mm_run"

        if root.get("start_datetime") is None:
            root["start_datetime"] = self._date_first_cycle_mm
        if root.get("end_datetime") is None:
            root["end_datetime"] = self._date_last_cycle_mm

        if root.get("cartopy_data_dir") is None:
            root["cartopy_data_dir"] = self._cartopy_data_dir

        return Config.from_default_yaml(self._platform, mm_parm["melodies_monet_parm"])

    @cached_property
    def _platform(self) -> PlatformKey:
        # return PlatformKey(self._find_nested_key_(("user", "MACHINE")).lower())
        return PlatformKey(self.user.MACHINE.lower())


    @cached_property
    def _datetime_first_cycl(self) -> datetime:
        return datetime.strptime(self._date_first_cycle_srw, "%Y%m%d%H")

    @cached_property
    def _datetime_last_cycl(self) -> datetime:
        return datetime.strptime(self._date_last_cycle_srw, "%Y%m%d%H")

    # @cached_property
    # def _yaml_data(self) -> dict[Path, YAMLConfig]:
    #     """Cache loaded YAML data from config files."""
    #     data = {}
    #     for yaml_path in self._yaml_srw_config_paths:
    #         data[yaml_path] = get_yaml_config(yaml_path)
    #     return data

    # @cached_property
    # def _yaml_srw_config_paths(self) -> tuple[Path, ...]:
    #     return self.config_path_user, self.config_path_rocoto, self.config_path_var_defns

    # def _find_nested_key_(self, key_tuple: tuple[str, ...]) -> Any:
    #     """Find a nested key in the YAML dictionaries using a tuple of string keys.
    #
    #     Args:
    #         key_tuple: Tuple of strings representing nested dictionary keys
    #
    #     Returns
    #     -------
    #         The value found at the nested key location
    #     """
    #     for yaml_path, yaml_dict in self._yaml_data.items():
    #         current = yaml_dict
    #         try:
    #             for key in key_tuple:
    #                 current = current[key]
    #             return current
    #         except KeyError:
    #             continue
    #         except:
    #             LOGGER(
    #                 f"unexpected error: {key_tuple=}, {type(current)=}",
    #                 level=logging.ERROR,
    #             )
    #             raise
    #     raise KeyError(f"{key_tuple=} not found in any YAML files: {self._yaml_data.keys()}")
