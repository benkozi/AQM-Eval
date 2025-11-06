"""Defines package objects used when generating MM files. A package is a collection of tasks specfiic to an evaluation type."""

import logging
import re
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Iterator, Literal

import cartopy  # type: ignore[import-untyped]
import dask
import matplotlib
import xarray as xr
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from melodies_monet import driver  # type: ignore[import-untyped]
from melodies_monet.driver import analysis  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.config import PackageConfig, PackageKey, TaskKey
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.mm_eval.driver.model import Model
from aqm_eval.settings import SETTINGS
from aqm_eval.shared import PathExisting, assert_directory_exists, calc_2d_chunks, get_or_create_path


class ForecastFileSpec(BaseModel):
    src_dir: PathExisting
    out_dir: PathExisting
    out_prefix: str
    forecast_hours: tuple[int, ...] = tuple(range(1, 25))

    @computed_field
    @cached_property
    def dyn_path(self) -> tuple[Path, ...]:
        fns = self.src_dir.glob("dynf*.nc")
        pattern = re.compile(r".*dynf0+\.nc")
        ret = [ii for ii in fns if re.match(pattern, ii.name) is None]
        return tuple(ret)

    @computed_field
    @cached_property
    def phy_path(self) -> tuple[Path, ...]:
        fns = self.src_dir.glob("phyf*.nc")
        pattern = re.compile(r".*phyf0+\.nc")
        ret = [ii for ii in fns if re.match(pattern, ii.name) is None]
        return tuple(ret)

    @computed_field
    @cached_property
    def out_path(self) -> Path:
        return self.out_dir / f"{self.out_prefix}.nc"


class AbstractEvalPackage(ABC, BaseModel):
    """Defines an abstract evaluation package."""

    model_config = {"frozen": True}
    ctx: AbstractDriverContext

    key: PackageKey = Field(description="MM package key.")
    namelist_template: str = Field(description="Package template file.")
    tasks_default: tuple[TaskKey, ...] = Field(description="Default tasks for the package.")

    @computed_field(description="Run directory for the MM evaluation package.")
    @cached_property
    def run_dir(self) -> Path:
        return self.ctx.mm_config.run_dir / self.key.value

    @computed_field(description="Directory containing links or derived files for package.")
    @cached_property
    def link_alldays_path(self) -> Path:
        return self.run_dir / "data"

    @computed_field(description="Output directory for the MM evaluation package.")
    @cached_property
    def output_dir(self) -> Path:
        return self.ctx.mm_config.output_dir / self.key.value

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        if len(self.ctx.mm_config.aqm.models) > 1:
            return self.tasks_default
        else:
            return tuple([ii for ii in self.tasks_default if not ii.name.startswith("SCORECARD")])

    @cached_property
    def task_control_filenames(self) -> set[str]:
        return set([f"control_{ii.value}.yaml" for ii in self.tasks])

    @cached_property
    def observation_template(self) -> str:
        return self.ctx.mm_config.aqm.packages[self.key].observation_template

    @cached_property
    def mm_models(self) -> tuple[Model, ...]:
        ret = []
        for k, v in self.ctx.mm_config.aqm.models.items():
            if self.ctx.mm_config.aqm.no_forecast and v.is_host:
                LOGGER(f"skipping host model {k=} as no_forecast is True")
                continue
            kwds = dict(
                cfg=v,
                dyn_file_template=("dynf*.nc",),
                link_alldays_path=self.link_alldays_path,
                date_range=self.ctx.mm_config.date_range,
            )
            ret.append(Model.model_validate(kwds))
        if len(ret) == 0:
            raise ValueError(f"no models found for package {self.key=}. At least one is required.")
        return tuple(ret)

    @cached_property
    def mm_model_labels(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            Model labels used for MM plotting.
        """
        return [mm_model.label for mm_model in self.mm_models]

    @cached_property
    def mm_model_titles_j2(self) -> str:
        """
        Returns
        -------
        list[str]
            Model titles used for MM plotting, converted into a format suitable for ``jinja2``.
        """
        return ", ".join([f'"{ii.cfg.title}"' for ii in self.mm_models])

    @cached_property
    def j2_env(self) -> Environment:
        """
        Returns
        -------
        Environment
            Jinja2 environment for rendering template files.
        """
        searchpath = self.ctx.template_dir
        LOGGER(f"creating J2 environment {searchpath=}")
        return Environment(
            loader=FileSystemLoader(searchpath=searchpath),
            undefined=StrictUndefined,
        )

    @cached_property
    def cfg(self) -> PackageConfig:
        return self.ctx.mm_config.aqm.packages[self.key]

    def iter_forecast_file_specs(self) -> Iterator[ForecastFileSpec]:
        date_range = self.ctx.mm_config.date_range
        for model in self.mm_models:
            expt_dir = model.cfg.expt_dir
            for curr_dt in date_range.iter_by_step():
                dir_path = expt_dir / date_range.to_srw_str(curr_dt)
                assert_directory_exists(dir_path)
                yield ForecastFileSpec(
                    src_dir=dir_path,
                    out_dir=model.link_alldays_path,
                    out_prefix=f"{model.label}_{dir_path.name}",
                )

    @log_it
    def initialize(self) -> None:
        """Initialize the runner. Create symlinks and control files for example.

        Returns
        -------
        None
        """
        LOGGER(f"{self.ctx=}")
        LOGGER(f"{self.key=}")

        _ = get_or_create_path(self.ctx.mm_config.output_dir)
        _ = get_or_create_path(self.ctx.mm_config.run_dir)
        _ = get_or_create_path(self.link_alldays_path, exist_ok=False)
        _ = get_or_create_path(self.output_dir, exist_ok=False)

        LOGGER("creating MM control configs")
        self._create_control_configs_()

    @log_it
    def run(
        self,
        task_key: TaskKey,
        finalize: bool = False,
    ) -> None:
        """Run the MM evaluation.

        task_key: TaskKey
            The task to run. The task may be skipped if the package does not support it. If skipped, a warning is issued.
        finalize: bool = False, optional
            If True, finalize the runner after the run completes, successfully or not.

        Returns
        -------
        None
        """
        LOGGER(f"{task_key=}")
        LOGGER(f"{finalize=}")

        if task_key not in self.tasks:
            LOGGER(exc_info=ValueError(f"{task_key=} not in {self.tasks=}. returning."))

        assert self.run_dir.exists()

        try:
            matplotlib.use("Agg")
            cartopy.config["data_dir"] = self.ctx.mm_config.cartopy_data_dir
            dask.config.set({"array.slicing.split_large_chunks": True})
            an = driver.analysis()
            control_yaml = self.run_dir / f"control_{task_key.value}.yaml"
            LOGGER(f"{control_yaml=}")
            an.control = control_yaml
            an.read_control()

            self._run_task_(an, task_key)
        finally:
            if finalize:
                self.finalize()

    @staticmethod
    @log_it
    def _run_task_(an: analysis, task: TaskKey) -> None:
        match task:
            case TaskKey.SAVE_PAIRED:
                an.open_models()
                an.open_obs()
                an.pair_data()
                an.save_analysis()
            case TaskKey.SPATIAL_OVERLAY | TaskKey.SPATIAL_BIAS:
                an.read_analysis()
                an.open_models()
                an.plotting()
            case TaskKey.STATS:
                an.read_analysis()
                an.stats()
            case _:
                an.read_analysis()
                an.plotting()

    @log_it
    def finalize(self) -> None:
        """Finalize the runner.

        Returns
        -------
        None
        """
        ...

    def _create_control_configs_(self) -> None:
        package_run_dir = self.run_dir
        LOGGER(f"{package_run_dir=}")
        if not package_run_dir.exists():
            LOGGER(f"{package_run_dir=} does not exist. creating.")
            package_run_dir.mkdir(parents=True, exist_ok=False)

        out_mm_cfg = package_run_dir / "melodies_monet_parm.yaml"
        out_mm_cfg.write_text(yaml.safe_dump(self.ctx.mm_config.to_yaml(), sort_keys=False))

        cfg = {"ctx": self.ctx, "mm_tasks": tuple([ii.value for ii in self.tasks]), "package": self}
        namelist_config_str = self.j2_env.get_template(self.namelist_template).render(cfg)
        namelist_config = yaml.safe_load(namelist_config_str)
        with open(package_run_dir / "namelist.yaml", "w") as f:
            f.write(namelist_config_str)
        namelist_config["package"] = self

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
            config_yaml = template.render({**namelist_config})
            curr_control_path = package_run_dir / f"control_{task}.yaml"
            LOGGER(f"{curr_control_path=}")
            with open(curr_control_path, "w") as f:
                f.write(config_yaml)


class AbstractDaskOperation(ABC, BaseModel):
    model_config = {"frozen": True}

    out_path: Path
    dyn_path: tuple[Path, ...]
    phy_path: tuple[Path, ...]
    dask_num_workers: int
    surf_only: bool
    chunks: dict[str, int] | Literal["auto", "auto-aqm-eval"] = {"time": 1}

    dyn_varnames: tuple[str, ...]
    phy_varnames: tuple[str, ...]
    derived_varnames: tuple[str, ...]

    def run(self) -> xr.Dataset:
        dask.config.set(scheduler="threads", num_workers=self.dask_num_workers)
        local_log_level = logging.DEBUG

        phy_dataset = self._open_dataset_("phy_path")
        dyn_dataset = self._open_dataset_("dyn_path")

        try:
            LOGGER("Create the combined dataset from physics and dynamics", level=local_log_level)
            new_fields_dyn = {ii: dyn_dataset[ii] for ii in self.dyn_varnames}
            new_fields_phy = {ii: phy_dataset[ii] for ii in self.phy_varnames}
            new_fields = {**new_fields_dyn, **new_fields_phy}
            LOGGER("Create merged dataset", level=local_log_level)
            ds = xr.Dataset(new_fields)
            ds.attrs = dyn_dataset.attrs

            LOGGER("Before compute derived fields", level=local_log_level)
            ds = self._compute_derived_fields_(ds)
            LOGGER("After compute derived fields", level=local_log_level)

            LOGGER("Before ds.compute", level=local_log_level)
            ds = ds.compute()
            LOGGER("After ds.compute", level=local_log_level)
        finally:
            dyn_dataset.close()
            phy_dataset.close()

        LOGGER(f"Save the combined dataset: {self.out_path}", level=local_log_level)
        ds.to_netcdf(self.out_path)

        return ds

    @dask.delayed
    @abstractmethod
    def _compute_derived_fields_(self, ds: xr.Dataset) -> xr.Dataset: ...

    def _open_dataset_(self, target: Literal["phy_path", "dyn_path"]) -> xr.Dataset:
        path = getattr(self, target)
        local_log_level = logging.DEBUG
        LOGGER(f"Load {path}", level=local_log_level)
        local_chunks: dict[str, int] | Literal["auto"] = "auto"
        if self.chunks == "auto-aqm-eval":
            with xr.open_mfdataset(path, concat_dim="time", combine="nested") as ds:
                dims_to_chunk = {ii: ds.sizes[ii] for ii in ["grid_xt", "grid_yt"]}
                local_chunks = calc_2d_chunks(dims_to_chunk, self.dask_num_workers - ds.sizes["time"])
            LOGGER(f"calculated chunks {local_chunks=}", level=local_log_level)
        else:
            local_chunks = self.chunks
        ds = xr.open_mfdataset(path, chunks=local_chunks, concat_dim="time", combine="nested")
        LOGGER(f"xr.open_mfdataset {ds=}", level=local_log_level)
        if self.surf_only:
            ds = ds.isel(pfull=slice(0, 1))
            if "phalf" in ds.dims:
                ds = ds.isel(phalf=slice(0, 1))
            if "ak" in ds.attrs:
                ds.attrs["ak"] = ds.attrs["ak"][0:2]
            if "bk" in ds.attrs:
                ds.attrs["bk"] = ds.attrs["bk"][0:2]
        LOGGER(f"{ds.dims=}", level=local_log_level)
        if self.chunks == "auto":
            ds = ds.chunk(self.chunks)
        LOGGER(f"exiting _open_dataset_ {ds=}", level=local_log_level)
        return ds


class AbstractDaskEvalPackage(AbstractEvalPackage):
    klass_dask_operation: type[AbstractDaskOperation]

    @log_it
    def initialize(self) -> None:
        super().initialize()
        self._run_dask_operations_()

    @log_it
    def _run_dask_operations_(self) -> None:
        for spec in self.iter_forecast_file_specs():
            LOGGER(f"{spec=}")
            op = self.klass_dask_operation.model_validate(
                dict(
                    out_path=spec.out_path,
                    dyn_path=spec.dyn_path,
                    phy_path=spec.phy_path,
                    dask_num_workers=SETTINGS.dask_num_workers,
                    surf_only=True,
                )
            )
            op.run()


def package_key_to_class(key: PackageKey) -> type[AbstractEvalPackage]:
    from .aqs_pm import AQS_PM_EvalPackage
    from .aqs_voc import AQS_VOC_EvalPackage
    from .chem import ChemEvalPackage
    from .ish import ISH_EvalPackage

    mapping: dict[PackageKey, type[AbstractEvalPackage]] = {
        PackageKey.CHEM: ChemEvalPackage,
        PackageKey.ISH: ISH_EvalPackage,
        PackageKey.AQS_PM: AQS_PM_EvalPackage,
        PackageKey.AQS_VOC: AQS_VOC_EvalPackage,
    }
    return mapping[key]
