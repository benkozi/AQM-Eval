from functools import cached_property
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from pydantic import BaseModel

from aqm_eval.mm_eval.driver.package.aqs_pm import AQS_PM_PreprocessDaskOperation
from aqm_eval.mm_eval.driver.package.core import AbstractDaskOperation
from aqm_eval.mm_eval.driver.package.ish import ISH_PreprocessDaskOperation
from aqm_eval.shared import PathExisting


class ContextForDaskTest(BaseModel):
    model_config = {"frozen": True}

    root_dir: PathExisting
    klass: type[AbstractDaskOperation]

    dims: dict[str, int] = {"time": 1, "pfull": 64, "grid_yt": 20, "grid_xt": 10}
    global_attrs: dict[str, str] = {"foo": "bar", "bar": "foo"}

    @cached_property
    def op(self) -> AbstractDaskOperation:
        dyn_path = self.root_dir / "dyn.nc"
        self.dataset_dyn.to_netcdf(dyn_path)

        phy_path = self.root_dir / "phy.nc"
        self.dataset_phy.to_netcdf(phy_path)

        return self.klass.model_validate(
            dict(out_path=self.root_dir / "out.nc", dyn_path=dyn_path, phy_path=phy_path, dask_num_workers=2)
        )

    @cached_property
    def dataset_dyn(self) -> xr.Dataset:
        fields = {ii: self.create_data_array(ii, self.dims) for ii in self.klass.model_fields["dyn_varnames"].default}
        ret = xr.Dataset(fields)
        for k, v in self.global_attrs.items():
            ret.attrs[k] = v
        return ret

    @cached_property
    def dataset_phy(self) -> xr.Dataset:
        fields = {ii: self.create_data_array(ii, self.dims) for ii in self.klass.model_fields["phy_varnames"].default}
        ret = xr.Dataset(fields)
        for k, v in self.global_attrs.items():
            ret.attrs[k] = v
        return ret

    @staticmethod
    def create_data_array(name: str, dims: dict[str, int]) -> xr.DataArray:
        shape = tuple(ii for ii in dims.values())
        data = np.random.random(shape)
        return xr.DataArray(data, name=name, dims=tuple(ii for ii in dims.keys()))


@pytest.mark.parametrize("klass", [ISH_PreprocessDaskOperation, AQS_PM_PreprocessDaskOperation])
def test(tmp_path: Path, klass: type[AbstractDaskOperation]) -> None:
    np.random.seed(0)
    test_ctx = ContextForDaskTest(root_dir=tmp_path, klass=klass)
    result = test_ctx.op.run()
    expected_dims = test_ctx.dims
    assert result.dims == expected_dims
    expected_vars = set(result.data_vars)
    expected_vars.update({"pfull"})
    assert expected_vars == set(test_ctx.op.dyn_varnames + test_ctx.op.phy_varnames + test_ctx.op.derived_varnames)
    assert result.attrs == test_ctx.global_attrs
    result.to_netcdf(test_ctx.op.out_path)
