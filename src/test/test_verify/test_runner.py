import subprocess
from pathlib import Path

from aqm_eval.verify.context import VerifyPair, VerifyContext
from aqm_eval.verify.runner import run_verify
from test.shared import create_data_array
import xarray as xr

def test(tmp_path: Path) -> None:
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

    run_verify(ctx)