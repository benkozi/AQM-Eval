from functools import cached_property

from pydantic import computed_field

from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.model import ModelRole
from aqm_eval.mm_eval.driver.package.core import AbstractEvalPackage, PackageKey, TaskKey


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
        for spec in self.iter_forecast_file_specs():
            f_dyn = spec.dyn_path
            f_phy = spec.phy_path
            f_out = spec.out_path

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
