from functools import cached_property

import dask
import dask.array
import xarray as xr
from pydantic import computed_field

from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.model import ModelRole
from aqm_eval.mm_eval.driver.package.core import (
    AbstractDaskOperation,
    AbstractDaskOperationContext,
    AbstractEvalPackage,
    PackageKey,
    TaskKey,
)
from aqm_eval.settings import SETTINGS


class ISH_PrepContext(AbstractDaskOperationContext):
    dyn_varnames: tuple[str, ...] = ("time_iso", "lat", "lon", "pfull", "phalf", "delz", "dpres", "hgtsfc", "pressfc", "tmp")
    phy_varnames: tuple[str, ...] = ("tmp2m", "spfh2m", "ugrd10m", "vgrd10m")


class ISH_PreprocessDaskOperation(AbstractDaskOperation):
    @dask.delayed
    def _compute_derived_fields_(self, ds: xr.Dataset) -> xr.Dataset:
        ds["vapor"] = (ds["spfh2m"] / (1 - ds["spfh2m"])) * ds["pressfc"] / (0.622 + ds["spfh2m"] / (1 - ds["spfh2m"]))
        ds["vapor"].attrs["long_name"] = "2 meter water vapor pressure"
        ds["vapor"].attrs["units"] = "Pa"

        ds["dew_temp"] = (243.5 * dask.array.log((ds["vapor"] / 100) / 6.112)) / (
            17.269 - dask.array.log((ds["vapor"] / 100) / 6.112)
        )
        ds["dew_temp"].attrs["long_name"] = "2 meter dew point temperature"
        ds["dew_temp"].attrs["units"] = "C"

        ds["ws10m"] = dask.array.sqrt(ds["ugrd10m"] * ds["ugrd10m"] + ds["vgrd10m"] * ds["vgrd10m"])
        ds["ws10m"].attrs["long_name"] = "10 meter wind speed"
        ds["ws10m"].attrs["units"] = "m/s"

        ds["wd10m"] = 270 - (dask.array.arctan2(ds["vgrd10m"], ds["ugrd10m"]) * 180 / 3.1415)
        ds["wd10m"].attrs["long_name"] = "10 meter wind direction"
        ds["wd10m"].attrs["units"] = "degree"

        ds["wd10m"] = xr.where(ds["wd10m"] > 360, ds["wd10m"] - 360, ds["wd10m"])

        return ds


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
            ctx = ISH_PrepContext(
                out_path=spec.out_path,
                dyn_path=spec.dyn_path,
                phy_path=spec.phy_path,
                dask_num_workers=SETTINGS.dask_num_workers,
                chunks={"grid_xt": 100, "grid_yt": 100},
            )
            op = ISH_PreprocessDaskOperation(ctx=ctx)
            op.run()
            # result = run_ish_preprocess_computation(ctx)
            # LOGGER(f"writing processed file: {ctx.out_path}")
            # result.to_netcdf(ctx.out_path)


# @dask.delayed
# def ish_prep(ctx: AbstractDaskOperationContext) -> xr.Dataset:
#     local_log_level = logging.DEBUG
#
#     phy_dataset = open_dataset(ctx, "phy_path")
#     dyn_dataset = open_dataset(ctx, "dyn_path")
#
#     LOGGER("Create the combined dataset from physics and dynamics", level=local_log_level)
#     new_fields_dyn = {ii: dyn_dataset[ii] for ii in ctx.dyn_varnames}
#     new_fields_phy = {ii: phy_dataset[ii] for ii in ctx.phy_varnames}
#     new_fields = {**new_fields_dyn, **new_fields_phy}
#     ds = xr.Dataset(new_fields)
#
#     ds.attrs = dyn_dataset.attrs
#
#     ds["vapor"] = (ds["spfh2m"] / (1 - ds["spfh2m"])) * ds["pressfc"] / (0.622 + ds["spfh2m"] / (1 - ds["spfh2m"]))
#     ds["vapor"].attrs["long_name"] = "2 meter water vapor pressure"
#     ds["vapor"].attrs["units"] = "Pa"
#
#     ds["dew_temp"] = (243.5 * dask.array.log((ds["vapor"] / 100) / 6.112)) / (17.269 - dask.array.log((ds["vapor"] / 100) / 6.112))
#     ds["dew_temp"].attrs["long_name"] = "2 meter dew point temperature"
#     ds["dew_temp"].attrs["units"] = "C"
#
#     ds["ws10m"] = dask.array.sqrt(ds["ugrd10m"] * ds["ugrd10m"] + ds["vgrd10m"] * ds["vgrd10m"])
#     ds["ws10m"].attrs["long_name"] = "10 meter wind speed"
#     ds["ws10m"].attrs["units"] = "m/s"
#
#     ds["wd10m"] = 270 - (dask.array.arctan2(ds["vgrd10m"], ds["ugrd10m"]) * 180 / 3.1415)
#     ds["wd10m"].attrs["long_name"] = "10 meter wind direction"
#     ds["wd10m"].attrs["units"] = "degree"
#
#     ds["wd10m"] = xr.where(ds["wd10m"] > 360, ds["wd10m"] - 360, ds["wd10m"])
#
#     ds = ds.compute()
#
#     dyn_dataset.close()
#     phy_dataset.close()
#
#     return ds


# @log_it
# def run_ish_preprocess_computation(ctx: AbstractDaskOperationContext) -> xr.Dataset:
#     dask.config.set(scheduler="threads", num_workers=ctx.dask_num_workers)
#     result = ish_prep(ctx).compute()
#     return result
