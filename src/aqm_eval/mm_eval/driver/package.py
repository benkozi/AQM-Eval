"""Defines package objects used when generating MM files. A package is a collection of tasks specfiic to an evaluation type."""

import logging
import subprocess
from abc import ABC
from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path

import cartopy  # type: ignore[import-untyped]
import dask
import matplotlib
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from melodies_monet import driver  # type: ignore[import-untyped]
from melodies_monet.driver import analysis  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.mm_eval.driver.model import Model, ModelRole
from aqm_eval.shared import assert_file_exists, get_or_create_path


@unique
class TaskKey(StrEnum):
    """Unique MM task keys."""

    SAVE_PAIRED = "save_paired"
    TIMESERIES = "timeseries"
    TAYLOR = "taylor"
    SPATIAL_BIAS = "spatial_bias"
    SPATIAL_OVERLAY = "spatial_overlay"
    BOXPLOT = "boxplot"
    MULTI_BOXPLOT = "multi_boxplot"
    SCORECARD_RMSE = "scorecard_rmse"
    SCORECARD_IOA = "scorecard_ioa"
    SCORECARD_NMB = "scorecard_nmb"
    SCORECARD_NME = "scorecard_nme"
    CSI = "csi"
    STATS = "stats"


@unique
class PackageKey(StrEnum):
    """Unique MM package keys."""

    CHEM = "chem"
    ISH = "ish"
    AQS_PM = "aqs_pm"
    AQS_VOC = "aqs_voc"


class AbstractEvalPackage(ABC, BaseModel):
    """Defines an abstract evaluation package."""

    model_config = {"frozen": True}
    ctx: AbstractDriverContext
    key: PackageKey = Field(description="MM package key.")
    namelist_template: str = Field(description="Package template file.")

    @computed_field(description="Run directory for the MM evaluation package.")
    @cached_property
    def run_dir(self) -> Path:
        return self.ctx.mm_run_dir / self.key.value

    @computed_field(description="Directory containing links or derived files for package.")
    @cached_property
    def link_alldays_path(self) -> Path:
        return self.run_dir / "data"

    @computed_field(description="Output directory for the MM evaluation package.")
    @cached_property
    def mm_package_output_dir(self) -> Path:
        return self.ctx.mm_output_dir / self.key.value

    @computed_field(description="Prefix for each model role.")
    @cached_property
    def model_prefixes(self) -> dict[ModelRole, str]:
        return {ii: ii.value + "_orig" for ii in ModelRole}

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        if self.ctx.mm_base_model_expt_dir is not None:
            return tuple([ii for ii in TaskKey])
        else:
            return tuple([ii for ii in TaskKey if not ii.name.startswith("SCORECARD")])

    @cached_property
    def task_control_filenames(self) -> set[str]:
        return set([f"control_{ii.value}.yaml" for ii in self.tasks])

    @cached_property
    def mm_models(self) -> tuple[Model, ...]:
        """
        Returns
        -------
        tuple[Model, ...]
            The models to use in the evaluation. At most, this can contain two models: the
            "evaluation" model and an optional "base" model. If two models are returned,
            "scorecards" can be created.
        """
        ret = [
            Model(
                expt_dir=self.ctx.mm_eval_model_expt_dir,
                label="eval_aqm",
                title="Eval AQM",
                prefix=self.model_prefixes[ModelRole.EVAL],
                role=ModelRole.EVAL,
                dyn_file_template=("dynf*.nc",),
                cycle_dir_template=self.ctx.link_simulation,
                link_alldays_path=self.link_alldays_path,
            )
        ]
        if self.ctx.mm_base_model_expt_dir is not None:
            ret.append(
                Model(
                    expt_dir=self.ctx.mm_base_model_expt_dir,
                    label="base_aqm",
                    title="Base AQM",
                    prefix=self.model_prefixes[ModelRole.BASE],
                    role=ModelRole.BASE,
                    dyn_file_template=("dynf*.nc",),
                    cycle_dir_template=self.ctx.link_simulation,
                    link_alldays_path=self.link_alldays_path,
                )
            )
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
        return ", ".join([f'"{ii.title}"' for ii in self.mm_models])

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

    @log_it
    def initialize(self) -> None:
        """Initialize the runner. Create symlinks and control files for example.

        Returns
        -------
        None
        """
        LOGGER(f"{self.ctx=}")
        LOGGER(f"{self.key=}")

        _ = get_or_create_path(self.ctx.mm_output_dir)
        _ = get_or_create_path(self.ctx.mm_run_dir)
        _ = get_or_create_path(self.link_alldays_path, exist_ok=False)
        _ = get_or_create_path(self.mm_package_output_dir, exist_ok=False)

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
            LOGGER(f"{task_key=} not in {self.tasks=}. returning.", level=logging.WARN)
            return

        assert self.run_dir.exists()

        try:
            matplotlib.use("Agg")
            cartopy.config["data_dir"] = self.ctx.cartopy_data_dir
            dask.config.set({"array.slicing.split_large_chunks": True})
            an = driver.analysis()
            control_yaml = self.ctx.mm_run_dir / self.key.value / f"control_{task_key.value}.yaml"
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

        cfg = {"ctx": self.ctx, "mm_tasks": tuple([ii.value for ii in self.tasks]), "package": self}
        namelist_config_str = self.j2_env.get_template(self.namelist_template).render(cfg)
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

    @staticmethod
    def _run_ncap2_cmd_(cmd: list[str]) -> None:
        local_cmd = ["ncap2"] + cmd
        LOGGER(f"running ncap2 command: {local_cmd}")
        subprocess.check_call(local_cmd)

    @staticmethod
    def _run_ncks_cmd_(cmd: list[str]) -> None:
        local_cmd = ["ncks"] + cmd
        LOGGER(f"running ncks command: {local_cmd}")
        subprocess.check_call(local_cmd)


class ChemEvalPackage(AbstractEvalPackage):
    """Defines a chemistry evaluation package."""

    key: PackageKey = PackageKey.CHEM
    namelist_template: str = "namelist.chem.j2"

    @log_it
    def initialize(self) -> None:
        super().initialize()
        for model in self.mm_models:
            model.create_symlinks()


class ISH_EvalPackage(AbstractEvalPackage):
    """Defines an ISH (Integrated Surface Hourly) meteorological evaluation package."""

    key: PackageKey = PackageKey.ISH
    namelist_template: str = "namelist.ish.j2"

    @computed_field(description="Prefix for each model role.")
    @cached_property
    def model_prefixes(self) -> dict[ModelRole, str]:
        return {ii: ii.value + "_ish" for ii in ModelRole}

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        return (
            TaskKey.SAVE_PAIRED,
            TaskKey.TIMESERIES,
            TaskKey.TAYLOR,
            TaskKey.SPATIAL_BIAS,
            TaskKey.SPATIAL_OVERLAY,
            TaskKey.BOXPLOT,
            TaskKey.STATS,
        )

    def initialize(self) -> None:
        super().initialize()
        self._ish_conversion_()

    @log_it
    def _ish_conversion_(self) -> None:
        """
        Extract/calculate necessary variables from phy files for ISH meteorological evaluation.

        References:
            https://nco.sourceforge.net/nco.html#Examples-ncap2
            https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.dewpoint_from_specific_humidity.html
            https://library.wmo.int/records/item/41650-guide-to-instruments-and-methods-of-observation
            https://sgichuki.github.io/Atmo/
        """
        for model in self.mm_models:
            prefix = model.prefix
            out_dir = model.link_alldays_path
            expt_dir = model.expt_dir

            # Get directory list
            dirlist = []
            for dir_pattern in model.cycle_dir_template:
                dirlist += sorted([d for d in expt_dir.glob(dir_pattern) if d.is_dir()])

            if len(dirlist) == 0:
                msg = f"no cycle directories found in {expt_dir=}"
                LOGGER(msg, exc_info=ValueError(msg))

            for dir_path in dirlist:
                dir_name = dir_path.name

                for fhr in range(1, 25):
                    fhr_str = f"{fhr:02d}"
                    f_phy = dir_path / f"phyf0{fhr_str}.nc"
                    assert_file_exists(f_phy)
                    f_dyn = dir_path / f"dynf0{fhr_str}.nc"
                    assert_file_exists(f_dyn)
                    f_out = out_dir / f"{prefix}_{dir_name}_f0{fhr_str}.nc"

                    # Define ncap2 commands to run
                    ncap2_commands = (
                        # Initial ncap2 call (creates output file)
                        ["-v", "-s", "time_iso = time_iso", str(f_dyn), str(f_out)],
                        # Subsequent ncap2 calls with -A flag (append mode)
                        ["-A", "-v", "-s", "lat = lat", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "lon = lon", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "pfull = pfull", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "phalf = phalf", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "delz = delz", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "dpres = dpres", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "hgtsfc = hgtsfc", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "pressfc = pressfc", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "tmp = tmp", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "tmp2m = tmp2m", str(f_phy), str(f_out)],
                        [
                            "-A",
                            "-v",
                            "-s",
                            "vapor = (spfh2m / (1 - spfh2m)) * pressfc / (0.622 + spfh2m / (1 - spfh2m))",
                            "-s",
                            'vapor@long_name="2 meter water vapor pressure"; vapor@units="Pa"',
                            str(f_phy),
                            str(f_out),
                        ],
                        [
                            "-A",
                            "-v",
                            "-s",
                            "dew_temp = (243.5 * ln((vapor / 100) / 6.112)) / (17.269 - ln((vapor / 100) / 6.112))",
                            "-s",
                            'dew_temp@long_name="2 meter dew point temperature"; dew_temp@units="C"',
                            str(f_out),
                            str(f_out),
                        ],
                        [
                            "-A",
                            "-v",
                            "-s",
                            "ws10m = sqrt(ugrd10m * ugrd10m + vgrd10m * vgrd10m)",
                            "-s",
                            'ws10m@long_name="10 meter wind speed"; ws10m@units="m/s"',
                            str(f_phy),
                            str(f_out),
                        ],
                        [
                            "-A",
                            "-v",
                            "-s",
                            "wd10m = 270 - (atan2(vgrd10m, ugrd10m) * 180 / 3.1415)",
                            "-s",
                            "where(wd10m > 360) wd10m = wd10m - 360",
                            "-s",
                            'wd10m@long_name="10 meter wind direction"; wd10m@units="degree"',
                            str(f_phy),
                            str(f_out),
                        ],
                    )

                    # Execute all ncap2 commands
                    for cmd in ncap2_commands:
                        self._run_ncap2_cmd_(cmd)


class AQS_PM_EvalPackage(AbstractEvalPackage):
    """Defines a AQS PM evaluation package."""

    key: PackageKey = PackageKey.AQS_PM
    namelist_template: str = "namelist.aqs.pm.j2"

    @computed_field(description="Prefix for each model role.")
    @cached_property
    def model_prefixes(self) -> dict[ModelRole, str]:
        # We need to differentiate these model prefixes due to transformations required for meteorological variables.
        return {ii: ii.value + "_pm" for ii in ModelRole}

    def initialize(self) -> None:
        super().initialize()
        self._pm_conversion_()

    @log_it
    def _pm_conversion_(self) -> None:
        """
        Extract/calculate PM variables from phy and dyn files.

        References:
            https://nco.sourceforge.net/nco.html#Examples-ncap2
            https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.dewpoint_from_specific_humidity.html
            https://library.wmo.int/records/item/41650-guide-to-instruments-and-methods-of-observation
            https://sgichuki.github.io/Atmo/
        """
        for model in self.mm_models:
            prefix = model.prefix
            out_dir = model.link_alldays_path
            expt_dir = model.expt_dir

            # Get directory list
            dirlist = []
            for dir_pattern in model.cycle_dir_template:
                dirlist += sorted([d for d in expt_dir.glob(dir_pattern) if d.is_dir()])

            if len(dirlist) == 0:
                msg = f"no cycle directories found in {expt_dir=}"
                LOGGER(msg, exc_info=ValueError(msg))

            for dir_path in dirlist:
                dir_name = dir_path.name

                for fhr in range(1, 25):
                    fhr_str = f"{fhr:02d}"
                    f_phy = dir_path / f"phyf0{fhr_str}.nc"
                    assert_file_exists(f_phy)
                    f_dyn = dir_path / f"dynf0{fhr_str}.nc"
                    assert_file_exists(f_dyn)
                    f_out = out_dir / f"{prefix}_{dir_name}_f0{fhr_str}.nc"

                    # Define ncap2 commands to run
                    ncap2_commands_pre = (
                        # Initial ncap2 call (creates output file)
                        ["-v", "-s", "time_iso = time_iso", str(f_dyn), str(f_out)],
                        # Subsequent ncap2 calls with -A flag (append mode)
                        ["-A", "-v", "-s", "lat = lat", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "lon = lon", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "pfull = pfull", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "phalf = phalf", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "delz = delz", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "dpres = dpres", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "hgtsfc = hgtsfc", str(f_dyn), str(f_out)],
                        ["-A", "-v", "-s", "pressfc = pressfc", str(f_dyn), str(f_out)],  # Unit=Pa
                        ["-A", "-v", "-s", "tmp = tmp", str(f_dyn), str(f_out)],  # Unit=K
                        ["-A", "-v", "-s", "tmp2m = tmp2m", str(f_phy), str(f_out)],  # Unit=K
                        # Calculate Air Density near surface
                        [
                            "-A",
                            "-v",
                            "-s",
                            "air_density = (28.97*(pressfc-dpres))/(8.314*tmp)",
                            "-s",
                            'air_density@long_name="air density"; air_density@units="g/m3"',
                            str(f_out),
                        ],  # Unit = g/m3
                    )

                    # Append all PM2.5 species from Modes for AQS file out
                    ncks_cmd = [
                        "-A",
                        "-v",
                        "aso4i,aso4j,aso4k,ano3i,ano3j,ano3k,anh4i,anh4j,anh4k,aeci,aecj,aorgcj,aothri,aothrj,alvpo1i,alvpo1j,asvpo1i,asvpo1j,asvpo2i,asvpo2j,asvpo3j,aivpo1j,apoci,apocj,alvoo1i,alvoo2i,asvoo1i,asvoo2i,aiso1j,aiso2j,aiso3j,amt1j,amt2j,amt3j,amt4j,amt5j,amt6j,amtno3j,amthydj,aglyj,asqtj,aorgcj,aolgbj,aolgaj,alvoo1j,alvoo2j,asvoo1j,asvoo2j,asvoo3j,aavb1j,aavb2j,aavb3j,aavb4j,apcsoj",
                        str(f_dyn),
                        str(f_out),
                    ]

                    # Append all total PM2.5 fractions for AQS file out
                    ncks_cmd2 = ["-A", "-v", "pm25at,pm25ac,pm25co", str(f_dyn), str(f_out)]

                    # Additional ncap2 commands for PM2.5 species calculations (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                    ncap2_commands_post = (
                        # calculate PM2.5 Sulfate for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "pm25_so4 = 0.001*(aso4i*pm25at+aso4j*pm25ac+aso4k*pm25co)*air_density",
                            "-s",
                            'pm25_so4@long_name="PM25 Sulfate"; pm25_so4@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate PM2.5 Nitrate for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "pm25_no3 = 0.001*(ano3i*pm25at+ano3j*pm25ac+ano3k*pm25co)*air_density",
                            "-s",
                            'pm25_no3@long_name="PM25 Nitrate"; pm25_no3@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate PM2.5 Ammonium for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "pm25_nh4 = 0.001*(anh4i*pm25at+anh4j*pm25ac+anh4k*pm25co)*air_density",
                            "-s",
                            'pm25_nh4@long_name="PM25 Ammonium"; pm25_nh4@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate PM2.5 Elemental Carbon for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "pm25_ec = 0.001*(aeci*pm25at+aecj*pm25ac)*air_density",
                            "-s",
                            'pm25_ec@long_name="PM25 Elemental Carbon"; pm25_ec@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate POC i-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "poci = 0.001*(alvpo1i/1.39+asvpo1i/1.32+asvpo2i/1.26+apoci)*air_density",
                            "-s",
                            'poci@long_name="Primary Organic Carbon i-mode"; poci@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate POC j-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "pocj = 0.001*(alvpo1j/1.39+asvpo1j/1.32+asvpo2j/1.26+asvpo3j/1.21+aivpo1j/1.17+apocj)*air_density",
                            "-s",
                            'pocj@long_name="Primary Organic Carbon j-mode"; pocj@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate POC total (i+j mode) for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "poc = poci + pocj",
                            "-s",
                            'poc@long_name="Primary Organic Carbon (i+j)"; poc@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate SOC i-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "soci = 0.001*(alvoo1i/2.27+alvoo2i/2.06+asvoo1i/1.88+asvoo2i/1.73)*air_density",
                            "-s",
                            'soci@long_name="Secondary Organic Carbon i-mode"; soci@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate SOC j-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "socj = 0.001*(aiso1j/2.20+aiso2j/2.23+aiso3j/2.80+amt1j/1.67+amt2j/1.67+amt3j/1.72+"
                            "amt4j/1.53+amt5j/1.57+amt6j/1.40+amtno3j/1.90+amthydj/1.54+aglyj/2.13+asqtj/1.52+"
                            "aorgcj/2.00+aolgbj/2.10+aolgaj/2.50+alvoo1j/2.27+alvoo2j/2.06+asvoo1j/1.88+asvoo2j/1.73+"
                            "asvoo3j/1.60+aavb1j/2.70+aavb2j/2.35+aavb3j/2.17+aavb4j/1.99+apcsoj/2.00)*air_density",
                            "-s",
                            'socj@long_name="Secondary Organic Carbon j-mode"; socj@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate SOC total (i+j mode) for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "soc  = soci + socj",
                            "-s",
                            'soc@long_name="Secondary Organic Carbon (i+j)"; soc@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                        # calculate PM2.5 OC total (i+j mode) for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
                        [
                            "-A",
                            "-v",
                            "-s",
                            "pm25_oc   = (poci + soci)*pm25at+(pocj + socj)*pm25ac",
                            "-s",
                            'pm25_oc@long_name="PM25 Organic Carbon (i+j)"; pm25_oc@units="ug/m3"',
                            str(f_out),
                        ],  # Unit = ug/m3
                    )

                    # Execute all ncap2 commands
                    for cmd in ncap2_commands_pre:
                        self._run_ncap2_cmd_(cmd)

                    # Execute ncks commands
                    self._run_ncks_cmd_(ncks_cmd)
                    self._run_ncks_cmd_(ncks_cmd2)

                    # Execute PM species calculation commands
                    for cmd in ncap2_commands_post:
                        self._run_ncap2_cmd_(cmd)


class AQS_VOC_EvalPackage(AbstractEvalPackage):
    """Defines a AQS VOC evaluation package."""

    key: PackageKey = PackageKey.AQS_VOC
    namelist_template: str = "namelist.aqs.voc.j2"

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        return (
            TaskKey.SAVE_PAIRED,
            TaskKey.TIMESERIES,
            TaskKey.TAYLOR,
            TaskKey.SPATIAL_BIAS,
            TaskKey.SPATIAL_OVERLAY,
            TaskKey.BOXPLOT,
            TaskKey.MULTI_BOXPLOT,
            TaskKey.CSI,
            TaskKey.STATS,
        )

    @log_it
    def initialize(self) -> None:
        super().initialize()
        for model in self.mm_models:
            model.create_symlinks()


def package_key_to_class(key: PackageKey) -> type[AbstractEvalPackage]:
    mapping = {
        PackageKey.CHEM: ChemEvalPackage,
        PackageKey.ISH: ISH_EvalPackage,
        PackageKey.AQS_PM: AQS_PM_EvalPackage,
        PackageKey.AQS_VOC: AQS_VOC_EvalPackage,
    }
    return mapping[key]
