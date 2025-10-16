import time
from functools import cached_property
from pathlib import Path

import dask
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field, computed_field

import xarray as xr
import numpy as np

np.random.seed(0)

class DataForTest(BaseModel):
    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    y_shp: int = 2000
    x_shp: int = 1000

    @cached_property
    def field_array(self) -> xr.DataArray:
        shape = (self.y_shp, self.x_shp)
        data = np.random.random(shape)
        return xr.DataArray(data, dims=("y", "x"))

    @cached_property
    def dataset(self) -> xr.Dataset:
        return xr.Dataset({"field": self.field_array})


class DataForTestFactory(ModelFactory[DataForTest]):
    ...

@dask.delayed
def func(ds):
    ds['field'] *= 1000
    return ds


def test(tmp_path: Path) -> None:
    path = tmp_path / "test.nc"
    # actual = DataForTestFactory.build()

    actual = DataForTest()

    # print(actual.field_array)
    # print(actual.dataset)

    actual.dataset.to_netcdf(path)

    dask.config.set(scheduler="processes", num_workers=8)

    ds = xr.open_dataset(path, chunks={"y":10, "x": 5})
    print(ds)

    # added = ds["field"] + 1
    # print(added)

    lazy = func(ds)

    print(lazy)

    result = lazy.compute()
    print(result)



