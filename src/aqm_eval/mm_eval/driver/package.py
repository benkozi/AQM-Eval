"""Defines package objects used when generating MM files. A package is a collection of tasks specfiic to an evaluation type."""

import subprocess
from abc import ABC
from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.helpers import PathExisting
from aqm_eval.mm_eval.driver.model import Model, ModelRole


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
    MET = "met"  # tdk:last: should this be named ish or met?
    AQS_PM = "aqs_pm"
    AQS_VOC = "aqs_voc"


class AbstractEvalPackage(ABC, BaseModel):
    """Defines an abstract evaluation package."""

    model_config = {"frozen": True}
    root_dir: PathExisting = Field(description="Root directory for MM evaluation package.")
    mm_eval_model_expt_dir: PathExisting = Field(description="Experiment directory containing evaluation model output.")
    mm_base_model_expt_dir: PathExisting | None = Field(description="Experiment directory containing base model output.")
    link_simulation: tuple[str, ...]
    link_alldays_path: PathExisting
    key: PackageKey = Field(description="MM package key.")
    namelist_template: str = Field(description="Package template file.")

    @computed_field(description="Prefix for each model role.")
    @cached_property
    def model_prefixes(self) -> dict[ModelRole, str]:
        return {ii: ii.value for ii in ModelRole}

    @computed_field(description="Run directory for the MM evaluation package.")
    @cached_property
    def run_dir(self) -> Path:
        return self.root_dir / self.key.value

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        if self.mm_base_model_expt_dir is not None:
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
                expt_dir=self.mm_eval_model_expt_dir,
                label="eval_aqm",
                title="Eval AQM",
                prefix=self.model_prefixes[ModelRole.EVAL],
                role=ModelRole.EVAL,
                dyn_file_template=("dynf*.nc",),
                cycle_dir_template=self.link_simulation,
                link_alldays_path=self.link_alldays_path,
            )
        ]
        if self.mm_base_model_expt_dir is not None:
            ret.append(
                Model(
                    expt_dir=self.mm_base_model_expt_dir,
                    label="base_aqm",
                    title="Base AQM",
                    prefix=self.model_prefixes[ModelRole.BASE],
                    role=ModelRole.BASE,
                    dyn_file_template=("dynf*.nc",),
                    cycle_dir_template=self.link_simulation,
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

    def initialize(self) -> None:
        """Allows for package-specific initialization requirements."""
        ...


class ChemEvalPackage(AbstractEvalPackage):
    """Defines a chemistry evaluation package."""

    key: PackageKey = PackageKey.CHEM
    namelist_template: str = "namelist.chem.j2"


# tdk:last: should this be named ish or met?
class MetEvalPackage(AbstractEvalPackage):
    """Defines a meteorological evaluation package."""

    key: PackageKey = PackageKey.MET
    namelist_template: str = "namelist.met.j2"  # tdk:last: should this be named ish or met?

    @computed_field(description="Prefix for each model role.")
    @cached_property
    def model_prefixes(self) -> dict[ModelRole, str]:
        # We need to differentiate these model prefixes due to transformations required for meteorological variables.
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
        self._ish_conversion_()

    @log_it
    def _ish_conversion_(self) -> None:  # ="aqmv8p1.ish"):
        """
        Extract/calculate necessary variables from phy files for ISH met evaluation.

        References:
            https://nco.sourceforge.net/nco.html#Examples-ncap2
            https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.dewpoint_from_specific_humidity.html
            https://library.wmo.int/records/item/41650-guide-to-instruments-and-methods-of-observation
            https://sgichuki.github.io/Atmo/

        Args:
            expt_dir: Input directory containing experiment directories
            out_dir: Output directory for processed files
            prefix: Prefix for output filenames
        """
        for model in self.mm_models:
            prefix = model.prefix
            out_dir = model.link_alldays_path
            expt_dir = model.expt_dir

            # Get directory list
            # tdk: this needs "module load nco" to work
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
                    _assert_file_exists_(f_phy)
                    f_dyn = dir_path / f"dynf0{fhr_str}.nc"
                    _assert_file_exists_(f_dyn)
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

    @staticmethod
    def _run_ncap2_cmd_(cmd: list[str]) -> None:
        local_cmd = ["ncap2"] + cmd
        LOGGER(f"running ncap2 command: {local_cmd}")
        subprocess.check_call(local_cmd)


class AQS_PMEvalPackage(AbstractEvalPackage):
    """Defines a AQS PM evaluation package."""

    # tdk: check for initialize requirements for PM
    key: PackageKey = PackageKey.AQS_PM
    namelist_template: str = "namelist.aqs.pm.j2"


class AQS_VOCEvalPackage(AbstractEvalPackage):
    """Defines a AQS VOC evaluation package."""

    # tdk: check for initialize requirements for VOC
    key: PackageKey = PackageKey.AQS_VOC
    namelist_template: str = "namelist.aqs.voc.j2"


def _assert_file_exists_(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"path is not a file: {path}")


def package_key_to_class(key: PackageKey) -> type[AbstractEvalPackage]:
    mapping = {
        PackageKey.CHEM: ChemEvalPackage,
        PackageKey.MET: MetEvalPackage,
        PackageKey.AQS_PM: AQS_PMEvalPackage,
        PackageKey.AQS_VOC: AQS_VOCEvalPackage,
    }
    return mapping[key]
