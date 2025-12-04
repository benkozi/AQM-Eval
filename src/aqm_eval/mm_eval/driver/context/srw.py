"""Implements the Short-Range Weather (SRW) App driver context."""

from datetime import datetime
from functools import cached_property
from pathlib import Path

import yaml
from pydantic import computed_field
from uwtools.api.config import get_yaml_config

from aqm_eval.base import AeBaseModel
from aqm_eval.mm_eval.driver.config import Config, PlatformKey
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.settings import SETTINGS
from aqm_eval.shared import assert_directory_exists, update_left


def _convert_date_string_to_mm_(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d%H")
    return dt.strftime("%Y-%m-%d-%H:00:00")


class SrwWorkflow(AeBaseModel):
    EXPT_BASEDIR: Path
    EXPT_SUBDIR: str
    DATE_FIRST_CYCL: str
    DATE_LAST_CYCL_MM: str


class SrwPlatform(AeBaseModel):
    FIXshp: Path


class SrwUser(AeBaseModel):
    MACHINE: str


class SRWContext(AbstractDriverContext):
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

    @cached_property
    def _date_first_cycle_srw(self) -> str:
        return self.workflow.DATE_FIRST_CYCL

    @cached_property
    def _date_last_cycle_srw(self) -> str:
        return self.workflow.DATE_LAST_CYCL_MM

    @cached_property
    def _date_first_cycle_mm(self) -> str:
        return _convert_date_string_to_mm_(self._date_first_cycle_srw)

    @cached_property
    def _date_last_cycle_mm(self) -> str:
        return _convert_date_string_to_mm_(self._date_last_cycle_srw)

    @cached_property
    def _mm_output_dir_default(self) -> Path:
        return self.expt_dir / "mm_output"

    @cached_property
    def _cartopy_data_dir(self) -> Path:
        target_dir = self.platform.FIXshp
        return assert_directory_exists(target_dir).absolute().resolve(strict=True)

    @cached_property
    def mm_config(self) -> Config:
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
        return PlatformKey(self.user.MACHINE.lower())

    @cached_property
    def _datetime_first_cycl(self) -> datetime:
        return datetime.strptime(self._date_first_cycle_srw, "%Y%m%d%H")

    @cached_property
    def _datetime_last_cycl(self) -> datetime:
        return datetime.strptime(self._date_last_cycle_srw, "%Y%m%d%H")
