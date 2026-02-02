from pathlib import Path

import pytest
import xarray as xr

from aqm_eval.verify.context import VerifyContext, VerifyPair
from test.shared import create_data_array


@pytest.fixture
def verify_ctx(tmp_path: Path) -> VerifyContext:
    dims = {"time": 1, "lat": 10, "lon": 10}
    o3 = create_data_array("O3", dims)
    o3.encoding["_FillValue"] = -99.0
    pm = create_data_array("PM25_TOT", dims)
    pm.encoding["_FillValue"] = -99.0
    ds = xr.Dataset({"O3": o3, "PM25_TOT": pm})

    actual = Path("actual.nc")
    expected = Path("expected.nc")

    ds.to_netcdf(tmp_path / actual)
    ds.to_netcdf(tmp_path / expected)

    pair = VerifyPair(actual=actual, expected=expected)
    ctx = VerifyContext(verify_pairs=(pair,), baseline_dir=tmp_path, expt_dir=tmp_path)
    return ctx
