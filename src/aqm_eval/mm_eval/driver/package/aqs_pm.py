import logging

import dask
import xarray as xr

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.package.core import (
    AbstractDaskEvalPackage,
    AbstractDaskOperation,
)


class AQS_PM_PreprocessDaskOperation(AbstractDaskOperation):
    dyn_varnames: tuple[str, ...] = (
        "time_iso",
        "lat",
        "lon",
        "pfull",
        "phalf",
        "delz",
        "dpres",
        "hgtsfc",
        "pressfc",
        "tmp",
        "aso4i",
        "aso4j",
        "aso4k",
        "ano3i",
        "ano3j",
        "ano3k",
        "anh4i",
        "anh4j",
        "anh4k",
        "aeci",
        "aecj",
        "aorgcj",
        "aothri",
        "aothrj",
        "alvpo1i",
        "alvpo1j",
        "asvpo1i",
        "asvpo1j",
        "asvpo2i",
        "asvpo2j",
        "asvpo3j",
        "aivpo1j",
        "apoci",
        "apocj",
        "alvoo1i",
        "alvoo2i",
        "asvoo1i",
        "asvoo2i",
        "aiso1j",
        "aiso2j",
        "aiso3j",
        "amt1j",
        "amt2j",
        "amt3j",
        "amt4j",
        "amt5j",
        "amt6j",
        "amtno3j",
        "amthydj",
        "aglyj",
        "asqtj",
        "aorgcj",
        "aolgbj",
        "aolgaj",
        "alvoo1j",
        "alvoo2j",
        "asvoo1j",
        "asvoo2j",
        "asvoo3j",
        "aavb1j",
        "aavb2j",
        "aavb3j",
        "aavb4j",
        "apcsoj",
        "pm25at",
        "pm25ac",
        "pm25co",
    )
    phy_varnames: tuple[str, ...] = ("tmp2m",)
    derived_varnames: tuple[str, ...] = (
        "air_density",
        "pm25_so4",
        "pm25_no3",
        "pm25_nh4",
        "pm25_ec",
        "poci",
        "pocj",
        "poc",
        "soc",
        "soci",
        "socj",
        "pm25_oc",
    )

    @dask.delayed
    def _compute_derived_fields_(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Extract/calculate PM variables from phy and dyn files.

        References:
            https://nco.sourceforge.net/nco.html#Examples-ncap2
            https://unidata.github.io/MetPy/latest/api/generated/metpy.calc.dewpoint_from_specific_humidity.html
            https://library.wmo.int/records/item/41650-guide-to-instruments-and-methods-of-observation
            https://sgichuki.github.io/Atmo/
        """

        local_log_level = logging.DEBUG

        LOGGER("Calculate Air Density near surface", level=local_log_level)
        ds["air_density"] = (28.97 * (ds["pressfc"] - ds["dpres"])) / (8.314 * ds["tmp"])
        ds["air_density"].attrs["long_name"] = "air density"
        ds["air_density"].attrs["units"] = "g/m3"

        LOGGER("Calculate PM2.5 Sulfate for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["pm25_so4"] = (
            0.001 * (ds["aso4i"] * ds["pm25at"] + ds["aso4j"] * ds["pm25ac"] + ds["aso4k"] * ds["pm25co"]) * ds["air_density"]
        )
        ds["pm25_so4"].attrs["long_name"] = "PM25 Sulfate"
        ds["pm25_so4"].attrs["units"] = "ug/m3"

        LOGGER("Calculate PM2.5 Nitrate for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["pm25_no3"] = (
            0.001 * (ds["ano3i"] * ds["pm25at"] + ds["ano3j"] * ds["pm25ac"] + ds["ano3k"] * ds["pm25co"]) * ds["air_density"]
        )
        ds["pm25_no3"].attrs["long_name"] = "PM25 Nitrate"
        ds["pm25_no3"].attrs["units"] = "ug/m3"

        LOGGER("Calculate PM2.5 Ammonium for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["pm25_nh4"] = (
            0.001 * (ds["anh4i"] * ds["pm25at"] + ds["anh4j"] * ds["pm25ac"] + ds["anh4k"] * ds["pm25co"]) * ds["air_density"]
        )
        ds["pm25_nh4"].attrs["long_name"] = "PM25 Ammonium"
        ds["pm25_nh4"].attrs["units"] = "ug/m3"

        LOGGER("Calculate PM2.5 Elemental Carbon for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["pm25_ec"] = 0.001 * (ds["aeci"] * ds["pm25at"] + ds["aecj"] * ds["pm25ac"]) * ds["air_density"]
        ds["pm25_ec"].attrs["long_name"] = "PM25 Elemental Carbon"
        ds["pm25_ec"].attrs["units"] = "ug/m3"

        LOGGER("Calculate POC i-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["poci"] = 0.001 * (ds["alvpo1i"] / 1.39 + ds["asvpo1i"] / 1.32 + ds["asvpo2i"] / 1.26 + ds["apoci"]) * ds["air_density"]
        ds["poci"].attrs["long_name"] = "Primary Organic Carbon i-mode"
        ds["poci"].attrs["units"] = "ug/m3"

        LOGGER("Calculate POC j-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["pocj"] = (
            0.001
            * (
                ds["alvpo1j"] / 1.39
                + ds["asvpo1j"] / 1.32
                + ds["asvpo2j"] / 1.26
                + ds["asvpo3j"] / 1.21
                + ds["aivpo1j"] / 1.17
                + ds["apocj"]
            )
            * ds["air_density"]
        )
        ds["pocj"].attrs["long_name"] = "Primary Organic Carbon j-mode"
        ds["pocj"].attrs["units"] = "ug/m3"

        LOGGER("Calculate POC total (i+j mode) for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["poc"] = ds["poci"] + ds["pocj"]
        ds["poc"].attrs["long_name"] = "Primary Organic Carbon (i+j)"
        ds["poc"].attrs["units"] = "ug/m3"

        LOGGER("Calculate SOC i-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["soci"] = (
            0.001 * (ds["alvoo1i"] / 2.27 + ds["alvoo2i"] / 2.06 + ds["asvoo1i"] / 1.88 + ds["asvoo2i"] / 1.73) * ds["air_density"]
        )
        ds["soci"].attrs["long_name"] = "Secondary Organic Carbon i-mode"
        ds["soci"].attrs["units"] = "ug/m3"

        LOGGER("Calculate SOC j-mode for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["socj"] = (
            0.001
            * (
                ds["aiso1j"] / 2.20
                + ds["aiso2j"] / 2.23
                + ds["aiso3j"] / 2.80
                + ds["amt1j"] / 1.67
                + ds["amt2j"] / 1.67
                + ds["amt3j"] / 1.72
                + ds["amt4j"] / 1.53
                + ds["amt5j"] / 1.57
                + ds["amt6j"] / 1.40
                + ds["amtno3j"] / 1.90
                + ds["amthydj"] / 1.54
                + ds["aglyj"] / 2.13
                + ds["asqtj"] / 1.52
                + ds["aorgcj"] / 2.00
                + ds["aolgbj"] / 2.10
                + ds["aolgaj"] / 2.50
                + ds["alvoo1j"] / 2.27
                + ds["alvoo2j"] / 2.06
                + ds["asvoo1j"] / 1.88
                + ds["asvoo2j"] / 1.73
                + ds["asvoo3j"] / 1.60
                + ds["aavb1j"] / 2.70
                + ds["aavb2j"] / 2.35
                + ds["aavb3j"] / 2.17
                + ds["aavb4j"] / 1.99
                + ds["apcsoj"] / 2.00
            )
            * ds["air_density"]
        )
        ds["socj"].attrs["long_name"] = "Secondary Organic Carbon j-mode"
        ds["socj"].attrs["units"] = "ug/m3"

        LOGGER("Calculate SOC total (i+j mode) for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["soc"] = ds["soci"] + ds["socj"]
        ds["soc"].attrs["long_name"] = "Secondary Organic Carbon (i+j)"
        ds["soc"].attrs["units"] = "ug/m3"

        LOGGER("Calculate PM2.5 OC total (i+j mode) for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)", level=local_log_level)
        ds["pm25_oc"] = (ds["poci"] + ds["soci"]) * ds["pm25at"] + (ds["pocj"] + ds["socj"]) * ds["pm25ac"]
        ds["pm25_oc"].attrs["long_name"] = "PM25 Organic Carbon (i+j)"
        ds["pm25_oc"].attrs["units"] = "ug/m3"

        return ds


class AQS_PM_EvalPackage(AbstractDaskEvalPackage):
    """Defines a AQS PM evaluation package."""

    key: PackageKey = PackageKey.AQS_PM
    observations_title: str = "AQS"
    namelist_template: str = "namelist.aqs.pm.j2"
    tasks_default: tuple[TaskKey, ...] = tuple(TaskKey)
    klass_dask_operation: type[AbstractDaskOperation] = AQS_PM_PreprocessDaskOperation
