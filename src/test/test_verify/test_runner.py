import subprocess
from pathlib import Path

from aqm_eval.verify.context import VerifyPair, VerifyContext
from test.shared import create_data_array
import xarray as xr

def test(tmp_path: Path) -> None:
    dims = {"time": 1, "lat": 10, "lon": 10}
    o3 = create_data_array("O3", dims)
    o3.encoding["_FillValue"] = -99.0
    pm = create_data_array("PM25_TOT", dims)
    pm.encoding["_FillValue"] = -99.0
    ds = xr.Dataset({"O3": o3, "PM25_TOT": pm})

    actual = tmp_path / "actual.nc"
    expected = tmp_path / "expected.nc"

    ds.to_netcdf(actual)
    ds.to_netcdf(expected)

    pair = VerifyPair(actual=actual, expected=expected)
    ctx = VerifyContext(verify_pairs=(pair,))

    v = ",".join(ctx.variables)

    cmd = ["nccmp", "-d", "-m", "-v", v, "-t", str(ctx.tolerance), str(ctx.verify_pairs[0].actual), str(ctx.verify_pairs[0].expected)]
    print(cmd)
    subprocess.check_call(cmd)