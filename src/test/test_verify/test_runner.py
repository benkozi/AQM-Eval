from pathlib import Path

import pytest
import xarray as xr
from box import Box

from aqm_eval.verify.context import VerifyContext, VerifyPair
from aqm_eval.verify.runner import NccmpError, run_verify


def test(verify_ctx: VerifyContext) -> None:
    print(verify_ctx.model_dump_json(indent=2))
    run_verify(verify_ctx)


@pytest.mark.parametrize("fail_fast", ["__default__", True])
def test_netcdf_values_differ(verify_ctx: VerifyContext, tmp_path: Path, fail_fast: str | bool) -> None:
    with xr.open_dataset(verify_ctx.verify_pairs_full_path[0].actual) as ds:
        ds_new = ds.copy()
    ds_new["O3"].data += 1
    actual2_path = tmp_path / "actual2.nc"
    ds_new.to_netcdf(actual2_path)
    data = Box(verify_ctx.model_dump(mode="json"))
    new_verify_pair = VerifyPair(actual=Path(actual2_path.name), expected=verify_ctx.verify_pairs[0].expected)
    data.verify_pairs.append(new_verify_pair)
    if fail_fast != "__default__":
        data.fail_fast = fail_fast
    new_verify_ctx = VerifyContext.model_validate(data)
    print(new_verify_ctx)
    with pytest.raises(NccmpError):
        run_verify(new_verify_ctx)
