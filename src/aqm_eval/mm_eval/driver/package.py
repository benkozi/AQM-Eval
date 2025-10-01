"""Defines package objects used when generating MM files. A package is a collection of tasks specfiic to an evaluation type."""
import subprocess
from abc import ABC
from enum import StrEnum, unique
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.helpers import PathExisting


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
    AQS_PM25 = "aqs_pm25"
    VOCS = "vocs"


class AbstractEvalPackage(ABC, BaseModel):
    """Defines an abstract evaluation package."""

    model_config = {"frozen": True}
    root_dir: PathExisting = Field(description="Root directory for MM evaluation package.")
    use_base_model: bool = Field(description="If True, a base model will be used to generate scorecards.")
    key: PackageKey = Field(description="MM package key.")
    namelist_template: str = Field(description="Package template file.")

    @computed_field(description="Run directory for the MM evaluation package.")
    @cached_property
    def run_dir(self) -> Path:
        return self.root_dir / self.key.value

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        if self.use_base_model:
            return tuple([ii for ii in TaskKey])
        else:
            return tuple([ii for ii in TaskKey if not ii.name.startswith("SCORECARD")])

    @cached_property
    def task_control_filenames(self) -> set[str]:
        return set([f"control_{ii.value}.yaml" for ii in self.tasks])

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
        self._ish_conv_(self.root_dir, self.run_dir, "aqmv8p1")

    @staticmethod
    @log_it
    def _ish_conv_(in_dir: Path, out_dir: Path, prefix: str) -> None: #="aqmv8p1.ish"):
        """
        Extract/calculate necessary variables from phy files for ISH met evaluation.

        References:
            https://nco.sourceforge.net/nco.html#Examples-ncap2
            https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.dewpoint_from_specific_humidity.html
            https://library.wmo.int/records/item/41650-guide-to-instruments-and-methods-of-observation
            https://sgichuki.github.io/Atmo/

        Args:
            in_dir: Input directory containing experiment directories
            out_dir: Output directory for processed files
            prefix: Prefix for output filenames
        """
        in_dir = Path(in_dir)
        out_dir = Path(out_dir)

        # Get directory list
        #tdk: glob needs to be a parameter
        #tdk: this needs "module load nco" to work
        dirlist = sorted([d for d in in_dir.glob("202402*/") if d.is_dir()])

        for dir_path in dirlist:
            dir_name = dir_path.name

            for fhr in range(1, 25):
                fhr_str = f"{fhr:02d}"
                f_phy = dir_path / f"phyf0{fhr_str}.nc"
                f_dyn = dir_path / f"dynf0{fhr_str}.nc"
                f_out = out_dir / f"{prefix}_{dir_name}_f0{fhr_str}.nc"

                # Initial ncap2 call (creates output file)
                subprocess.check_call(["ncap2", "-v", "-s", "time_iso = time_iso", str(f_dyn), str(f_out)])

                # Subsequent ncap2 calls with -A flag (append mode)
                subprocess.check_call(["ncap2", "-A", "-v", "-s", "lat = lat", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "lon = lon", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "pfull = pfull", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "phalf = phalf", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "delz = delz", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "dpres = dpres", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "hgtsfc = hgtsfc", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "pressfc = pressfc", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "tmp = tmp", str(f_dyn), str(f_out)])

                subprocess.check_call(["ncap2", "-A", "-v", "-s", "tmp2m = tmp2m", str(f_phy), str(f_out)])

                subprocess.check_call([
                    "ncap2", "-A", "-v",
                    "-s", "vapor = (spfh2m / (1 - spfh2m)) * pressfc / (0.622 + spfh2m / (1 - spfh2m))",
                    "-s", 'vapor@long_name="2 meter water vapor pressure"; vapor@units="Pa"',
                    str(f_phy), str(f_out)
                ])

                subprocess.check_call([
                    "ncap2", "-A", "-v",
                    "-s", "dew_temp = (243.5 * ln((vapor / 100) / 6.112)) / (17.269 - ln((vapor / 100) / 6.112))",
                    "-s", 'dew_temp@long_name="2 meter dew point temperature"; dew_temp@units="C"',
                    str(f_out), str(f_out)
                ])

                subprocess.check_call([
                    "ncap2", "-A", "-v",
                    "-s", "ws10m = sqrt(ugrd10m * ugrd10m + vgrd10m * vgrd10m)",
                    "-s", 'ws10m@long_name="10 meter wind speed"; ws10m@units="m/s"',
                    str(f_phy), str(f_out)
                ])

                subprocess.check_call([
                    "ncap2", "-A", "-v",
                    "-s", "wd10m = 270 - (atan2(vgrd10m, ugrd10m) * 180 / 3.1415)",
                    "-s", "where(wd10m > 360) wd10m = wd10m - 360",
                    "-s", 'wd10m@long_name="10 meter wind direction"; wd10m@units="degree"',
                    str(f_phy), str(f_out)
                ])
