import dask
import dask.array
import numpy as np
import xarray as xr

from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.package.core import (
    AbstractDaskEvalPackage,
    AbstractDaskOperation,
)


class ISH_PreprocessDaskOperation(AbstractDaskOperation):
    dyn_varnames: tuple[str, ...] = ("time_iso", "lat", "lon", "pfull", "phalf", "delz", "dpres", "hgtsfc", "pressfc", "tmp")
    phy_varnames: tuple[str, ...] = ("tmp2m", "spfh2m", "ugrd10m", "vgrd10m")
    derived_varnames: tuple[str, ...] = ("vapor", "dew_temp", "ws10m", "wd10m", "rh2m")

    @dask.delayed
    def _compute_derived_fields_(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Calculate derived variables for ISH meteorological evaluation.

        References:
            https://nco.sourceforge.net/nco.html#Examples-ncap2
            https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.dewpoint_from_specific_humidity.html
            https://library.wmo.int/records/item/41650-guide-to-instruments-and-methods-of-observation
            https://sgichuki.github.io/Atmo/
        """

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
        ds["wd10m"] = xr.where(ds["wd10m"] > 360, ds["wd10m"] - 360, ds["wd10m"])
        ds["wd10m"].attrs["long_name"] = "10 meter wind direction"
        ds["wd10m"].attrs["units"] = "degree"

        # Convert temperature fields to Celsius
        ds["tmp"] -= 273.15
        ds["tmp"].attrs["units"] = "C"
        ds["tmp2m"] -= 273.15
        ds["tmp2m"].attrs["units"] = "C"

        # Calculate RH from specific humidity per Zach Moon's calc-met.py (spike/calc-met.py)
        #   Note: ds["spfh2m"].attrs["units"] == "kg/kg"
        pres = 1000_00  # Pa
        e_s = 6.1094 * 100 * dask.array.exp(17.625 * ds["tmp2m"] / (ds["tmp2m"] + 243.04))  # saturation VP; Pa
        w_s = 0.622 * e_s / pres
        rh = 100 * ds["spfh2m"] / w_s
        if not (rh.min() > 0 and rh.quantile(0.9) < 100):
            raise ValueError(f"rh quantile check failed: {rh.quantile(0.9)=}")
        rh = rh.astype(np.float32)
        ds["rh2m"] = rh
        ds["rh2m"].attrs.update(long_name="2-m relative humidity", units="%")

        return ds


class ISH_EvalPackage(AbstractDaskEvalPackage):
    """Defines an ISH (Integrated Surface Hourly) meteorological evaluation package."""

    key: PackageKey = PackageKey.ISH
    observations_title: str = "ISH"
    observations_label: str = "ish"
    tasks_default: tuple[TaskKey, ...] = (
        TaskKey.SAVE_PAIRED,
        TaskKey.TIMESERIES,
        TaskKey.TAYLOR,
        TaskKey.SPATIAL_BIAS,
        TaskKey.SPATIAL_OVERLAY,
        TaskKey.BOXPLOT,
        TaskKey.STATS,
    )
    klass_dask_operation: type[AbstractDaskOperation] = ISH_PreprocessDaskOperation
