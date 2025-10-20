from functools import cached_property
from pathlib import Path

import numpy as np
import xarray as xr
from pydantic import BaseModel

from aqm_eval.mm_eval.driver.package.aqs_pm import PM_PrepContext, run_pm_preprocess_computation
from aqm_eval.shared import PathExisting


def fake_run_pm_preprocess_computation(mm_prep_ctx: PM_PrepContext) -> xr.Dataset:
    assert not mm_prep_ctx.out_path.exists()
    mm_prep_ctx.out_path.touch()
    return xr.Dataset()


class ContextForTest(BaseModel):
    model_config = {"frozen": True}

    root_dir: PathExisting

    dims: dict[str, int] = {"time": 1, "pfull": 64, "grid_yt": 20, "grid_xt": 10}
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
    global_attrs: dict[str, str] = {"foo": "bar", "bar": "foo"}

    # @computed_field
    # @cached_property
    # def chunk(self) -> int:
    #     return int(self.x_shp / 2)

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

        return PM_PrepContext(
            out_path=self.root_dir / "out.nc",
            dyn_path=dyn_path,
            phy_path=phy_path,
            dask_num_workers=2,
        )

    @cached_property
    def dataset_dyn(self) -> xr.Dataset:
        fields = {ii: self.create_data_array(ii, self.dims) for ii in PM_PrepContext.model_fields["dyn_varnames"].default}
        ret = xr.Dataset(fields)
        for k, v in self.global_attrs.items():
            ret.attrs[k] = v
        return ret

    @cached_property
    def dataset_phy(self) -> xr.Dataset:
        fields = {ii: self.create_data_array(ii, self.dims) for ii in PM_PrepContext.model_fields["phy_varnames"].default}
        ret = xr.Dataset(fields)
        for k, v in self.global_attrs.items():
            ret.attrs[k] = v
        return ret

    @staticmethod
    def create_data_array(name: str, dims: dict[str, int]) -> xr.DataArray:
        shape = tuple(ii for ii in dims.values())
        data = np.random.random(shape)
        return xr.DataArray(data, name=name, dims=tuple(ii for ii in dims.keys()))


def test_run_pm_preprocess_computation(tmp_path: Path) -> None:
    # kwds = dict(out_path = tmp_path / "out.nc",
    # dyn_path = tmp_path / "dyn.nc",
    # phy_path = tmp_path / "phy.nc",
    #             chunks={"y": 500, "x": 500})
    # pm_prep_ctx = PM_PrepContext.model_validate(kwds)
    np.random.seed(0)

    test_ctx = ContextForTest(root_dir=tmp_path)

    # dask.config.set(scheduler="processes", num_workers=2)
    # dask.config.set(scheduler="threads", num_workers=test_ctx.pm_prep_ctx.dask_num_workers)
    # LOGGER(f"{dask.config.get('scheduler', default='not set')=}")
    # LOGGER(f"{dask.config.get('num_workers', default='not set')=}")
    # LOGGER(f"{dask.config.get('num_threads', default='not set')=}")

    # result = pm_prep(test_ctx.pm_prep_ctx).compute()

    result = run_pm_preprocess_computation(test_ctx.pm_prep_ctx)

    expected_dims = test_ctx.dims
    # expected_dims["pfull"] = 1
    assert result.dims == expected_dims

    expected_vars = set(result.data_vars)
    expected_vars.update({"pfull"})
    assert expected_vars == set(test_ctx.pm_prep_ctx.dyn_varnames + test_ctx.pm_prep_ctx.phy_varnames + test_ctx.derived_varnames)

    assert result.attrs == test_ctx.global_attrs

    # print(result)
    result.to_netcdf(test_ctx.pm_prep_ctx.out_path)
