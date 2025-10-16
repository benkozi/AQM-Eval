import time
from functools import cached_property
from pathlib import Path

import dask
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field, computed_field

import xarray as xr
import numpy as np

from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.shared import PathExisting

np.random.seed(0)

class PM_PrepContext(BaseModel):
    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    out_path: Path
    dyn_path: PathExisting
    phy_path: PathExisting
    chunks: dict[str, int]

    dyn_varnames: tuple[str, ...] = ("time_iso", "lat", "lon", "pfull", "phalf", "delz", "dpres", "hgtsfc", "pressfc", "tmp", "aso4i","aso4j","aso4k","ano3i","ano3j","ano3k","anh4i","anh4j","anh4k","aeci","aecj","aorgcj","aothri","aothrj","alvpo1i","alvpo1j","asvpo1i","asvpo1j","asvpo2i","asvpo2j","asvpo3j","aivpo1j","apoci","apocj","alvoo1i","alvoo2i","asvoo1i","asvoo2i","aiso1j","aiso2j","aiso3j","amt1j","amt2j","amt3j","amt4j","amt5j","amt6j","amtno3j","amthydj","aglyj","asqtj","aorgcj","aolgbj","aolgaj","alvoo1j","alvoo2j","asvoo1j","asvoo2j","asvoo3j","aavb1j","aavb2j","aavb3j","aavb4j","apcsoj", "pm25at", "pm25ac", "pm25co")
    phy_varnames: tuple[str, ...] = ("tmp2m",)


class ContextForTest(BaseModel):
    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    root_dir: PathExisting

    t_shp: int = 10
    y_shp: int = 20
    x_shp: int = 10

    derived_varnames: tuple[str, ...] = ("air_density", "pm25_so4", "pm25_no3", "pm25_nh4")

    @computed_field
    @cached_property
    def chunk(self) -> int:
        return int(self.x_shp / 2)

    # @cached_property
    # def field_array(self) -> xr.DataArray:
    #     shape = (self.y_shp, self.x_shp)
    #     data = np.random.random(shape)
    #     return xr.DataArray(data, dims=("y", "x"))
    
    @cached_property
    def pm_prep_ctx(self) -> PM_PrepContext:
        dyn_path = self.root_dir / "dyn.nc"
        self.dataset_dyn.to_netcdf(dyn_path)
        
        phy_path = self.root_dir / "phy.nc"
        self.dataset_phy.to_netcdf(phy_path)
        
        return PM_PrepContext(out_path=self.root_dir / "out.nc",
                              dyn_path=dyn_path,
                              phy_path=phy_path,
                              chunks={"y": self.chunk, "x": self.chunk})

    @cached_property
    def dataset_dyn(self) -> xr.Dataset:
        return xr.Dataset({ii: self.create_data_array(ii) for ii in PM_PrepContext.model_fields["dyn_varnames"].default})

    @cached_property
    def dataset_phy(self) -> xr.Dataset:
        return xr.Dataset({ii: self.create_data_array(ii) for ii in PM_PrepContext.model_fields["phy_varnames"].default})

    def create_data_array(self, name: str) -> xr.DataArray:
        shape = (self.t_shp, self.y_shp, self.x_shp)
        data = np.random.random(shape)
        return xr.DataArray(data, name=name, dims=("t", "y", "x"))

class ContextForTestFactory(ModelFactory[ContextForTest]):
    ...

@dask.delayed
def pm_prep(ctx: PM_PrepContext) -> xr.Dataset:

    # Load the physics and dynamics output from file
    phy_dataset = xr.open_dataset(ctx.phy_path, chunks=ctx.chunks)
    phy_dataset = phy_dataset.isel(t=slice(0, 1))
    dyn_dataset = xr.open_dataset(ctx.dyn_path, chunks=ctx.chunks)
    dyn_dataset = dyn_dataset.isel(t=slice(0, 1))

    # Create the combined dataset from physics and dynamics
    new_fields_dyn = {ii: dyn_dataset[ii] for ii in ctx.dyn_varnames}
    new_fields_phy = {ii: phy_dataset[ii] for ii in ctx.phy_varnames}
    new_fields = {**new_fields_dyn, **new_fields_phy}
    ds = xr.Dataset(new_fields)

    # Calculate Air Density near surface
    ds["air_density"] = (28.97 * (ds["pressfc"] - ds["dpres"])) / (8.314 * ds["tmp"])
    ds["air_density"].attrs["long_name"] = "air density"
    ds["air_density"].attrs["units"] = "g/m3"

    # Calculate PM2.5 Sulfate for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
    ds["pm25_so4"] = 0.001 * (ds["aso4i"] * ds["pm25at"] + ds["aso4j"] * ds["pm25ac"] + ds["aso4k"] * ds["pm25co"]) * ds["air_density"]
    ds["pm25_so4"].attrs["long_name"] = "PM25 Sulfate"
    ds["pm25_so4"].attrs["units"] = "ug/m3"

    # Calculate PM2.5 Nitrate for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
    ds["pm25_no3"] = 0.001 * (ds["ano3i"] * ds["pm25at"] + ds["ano3j"] * ds["pm25ac"] + ds["ano3k"] * ds["pm25co"]) * ds["air_density"]
    ds["pm25_no3"].attrs["long_name"] = "PM25 Nitrate"
    ds["pm25_no3"].attrs["units"] = "ug/m3"

    # Calculate PM2.5 Ammonium for AQS file out (based on CB6-AERO7 in AQMv8/CMAQv5.4)
    ds["pm25_nh4"] = 0.001 * (ds["anh4i"] * ds["pm25at"] + ds["anh4j"] * ds["pm25ac"] + ds["anh4k"] * ds["pm25co"]) * ds["air_density"]
    ds["pm25_nh4"].attrs["long_name"] = "PM25 Ammonium"
    ds["pm25_nh4"].attrs["units"] = "ug/m3"

    return ds



def test(tmp_path: Path) -> None:
    # kwds = dict(out_path = tmp_path / "out.nc",
    # dyn_path = tmp_path / "dyn.nc",
    # phy_path = tmp_path / "phy.nc",
    #             chunks={"y": 500, "x": 500})
    # pm_prep_ctx = PM_PrepContext.model_validate(kwds)

    test_ctx = ContextForTest(root_dir=tmp_path)

    dask.config.set(scheduler="processes", num_workers=2)

    processed = pm_prep(test_ctx.pm_prep_ctx)

    result = processed.compute()

    assert result.dims == {'t': 1, 'y': test_ctx.y_shp, 'x': test_ctx.x_shp}

    assert set(result.data_vars) == set(test_ctx.pm_prep_ctx.dyn_varnames + test_ctx.pm_prep_ctx.phy_varnames + test_ctx.derived_varnames)


    # actual = ContextForTestFactory.build()

    # actual = ContextForTest()
    #
    # # print(actual.field_array)
    # # print(actual.dataset)
    #
    # actual.dataset.to_netcdf(path)
    #
    # dask.config.set(scheduler="processes", num_workers=8)
    #
    # ds = xr.open_dataset(path, chunks={"y":10, "x": 5})
    # print(ds)
    #
    # # added = ds["field"] + 1
    # # print(added)
    #
    # lazy = func(ds)
    #
    # print(lazy)
    #
    # result = lazy.compute()
    # print(result)



