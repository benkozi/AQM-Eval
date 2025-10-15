"""Implements the pure YAML driver context for MM evaluation packages."""

from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, computed_field

from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.mm_eval.driver.helpers import PathExisting
from aqm_eval.mm_eval.driver.package import PackageKey


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
    def mm_base_model_expt_dir(self) -> PathExisting:
        return PathExisting(self._config_data["link_base_path"])

    @computed_field
    @cached_property
    def mm_eval_model_expt_dir(self) -> PathExisting:
        return PathExisting(self._config_data["link_eval_path"])

    @computed_field
    @cached_property
    def link_simulation(self) -> tuple[str, ...]:
        value = self._config_data["link_simulation"].replace("/", "")
        return tuple(value)

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
    def mm_package_key(self) -> PackageKey:
        return PackageKey(self._config_data["package_key"])

    @computed_field
    @cached_property
    def link_alldays_path(self) -> PathExisting:
        return _get_or_create_path_(self._config_data["link_Alldays_path"])

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
