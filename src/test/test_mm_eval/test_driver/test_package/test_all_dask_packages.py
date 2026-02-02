from functools import cached_property
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import xarray as xr
from pydantic import BaseModel

from aqm_eval.mm_eval.driver.package.aqs_pm import AQS_PM_PreprocessDaskOperation
from aqm_eval.mm_eval.driver.package.core import AbstractDaskOperation, ForecastFileSpec
from aqm_eval.mm_eval.driver.package.ish import ISH_PreprocessDaskOperation
from aqm_eval.shared import PathExisting
from test.shared import create_data_array


class ContextForDaskTest(BaseModel):
    model_config = {"frozen": True}

    root_dir: PathExisting
    klass: type[AbstractDaskOperation]
    surf_only: bool

    dims: dict[str, int] = {"time": 1, "pfull": 64, "grid_yt": 20, "grid_xt": 10}
    global_attrs: dict[str, Any] = {"foo": "bar", "bar": "foo"}
    n_files: int = 15

    @cached_property
    def op(self) -> AbstractDaskOperation:
        for ii in range(self.n_files):
            dyn_path = self.root_dir / f"dynf{ii}.nc"
            self.dataset_dyn.to_netcdf(dyn_path)

            phy_path = self.root_dir / f"phyf{ii}.nc"
            self.dataset_phy.to_netcdf(phy_path)

        spec = ForecastFileSpec(src_dir=self.root_dir, out_dir=self.root_dir, out_prefix="test")
        print(f"{spec.dyn_path=}")
        print(f"{spec.phy_path=}")

        return self.klass.model_validate(
            dict(
                out_path=self.root_dir / "out.nc",
                dyn_path=spec.dyn_path,
                phy_path=spec.phy_path,
                dask_num_workers=4,
                surf_only=self.surf_only,
                chunks="auto-aqm-eval",
            )
        )

    @cached_property
    def ak_bk_value(self) -> np.ndarray:
        return np.array(range(self.dims["pfull"] + 1))

    @cached_property
    def ak_bk_attrs(self) -> dict[str, np.ndarray]:
        if self.surf_only:
            return {"ak": self.ak_bk_value[0:2], "bk": self.ak_bk_value[0:2]}
        else:
            return {"ak": self.ak_bk_value, "bk": self.ak_bk_value}

    @cached_property
    def expected_global_attrs(self) -> dict[str, Any]:
        ret = self.global_attrs.copy()
        ret.update(self.ak_bk_attrs)
        for ii in ["ak", "bk"]:
            ret[ii] = ret[ii].tolist()
        return ret

    @cached_property
    def dataset_dyn(self) -> xr.Dataset:
        fields = {ii: create_data_array(ii, self.dims) for ii in self.klass.model_fields["dyn_varnames"].default}
        ret = xr.Dataset(fields)
        for k, v in self.global_attrs.items():
            ret.attrs[k] = v
        ret.attrs.update(self.ak_bk_attrs)
        return ret

    @cached_property
    def dataset_phy(self) -> xr.Dataset:
        fields = {ii: create_data_array(ii, self.dims) for ii in self.klass.model_fields["phy_varnames"].default}
        ret = xr.Dataset(fields)
        for k, v in self.global_attrs.items():
            ret.attrs[k] = v
        return ret


@pytest.fixture(params=[ISH_PreprocessDaskOperation, AQS_PM_PreprocessDaskOperation])
def klass(request: pytest.FixtureRequest) -> type[AbstractDaskOperation]:
    return request.param


@pytest.fixture(params=[True, False])
def surf_only(request: pytest.FixtureRequest) -> bool:
    return request.param


def test(tmp_path: Path, klass: type[AbstractDaskOperation], surf_only: bool) -> None:
    np.random.seed(0)
    test_ctx = ContextForDaskTest(root_dir=tmp_path, klass=klass, surf_only=surf_only)
    result = test_ctx.op.run()
    print(result)
    expected_dims = test_ctx.dims
    expected_dims["time"] = test_ctx.n_files - 1  # no f0.nc file
    if surf_only:
        expected_dims["pfull"] = 1
    assert result.dims == expected_dims
    expected_vars = set(result.data_vars)
    expected_vars.update({"pfull"})
    assert expected_vars == set(test_ctx.op.dyn_varnames + test_ctx.op.phy_varnames + test_ctx.op.derived_varnames)
    actual_attrs = result.attrs.copy()
    for ii in ["ak", "bk"]:
        actual_attrs[ii] = actual_attrs[ii].tolist()
    assert actual_attrs == test_ctx.expected_global_attrs
    result.to_netcdf(test_ctx.op.out_path)
