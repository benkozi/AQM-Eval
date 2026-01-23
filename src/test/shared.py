import numpy as np
import xarray as xr


def create_data_array(name: str, dims: dict[str, int]) -> xr.DataArray:
    shape = tuple(ii for ii in dims.values())
    data = np.random.random(shape)
    return xr.DataArray(data, name=name, dims=tuple(ii for ii in dims.keys()))
