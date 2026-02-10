from typing import Any
from unittest.mock import MagicMock
from pathlib import Path
import xarray as xr
import numpy as np

from aqm_eval.mm_eval.driver.package.ish import ISH_EvalPackage

def _run_check_epa_ecoregions_(tmp_path: Path, data_vars: dict[str, Any]) -> None:
    path = tmp_path / "paired_file1.nc"
    ds = xr.Dataset(data_vars=data_vars)
    ds.to_netcdf(path)

    # Mock self fields
    pkg = MagicMock(spec=ISH_EvalPackage)
    pkg.paired_filenames = {"model1": "paired_file1.nc"}
    pkg.output_dir = tmp_path

    ISH_EvalPackage._check_for_epa_ecoregions_and_add_if_not_exists_(pkg)
    return path

def test_check_for_epa_ecoregions_and_add_if_not_exists_epa_region_exists(tmp_path: Path) -> None:
    # Setup: Create a dataset where 'epa_region' already exists
    data_vars = {
        "epa_region": (["x"], [1, 2, 3]),
        "state": (["x"], ["AL", "AL", "AL"])
    }
    path = _run_check_epa_ecoregions_(tmp_path, data_vars)

    # Verify dataset was NOT modified (or at least epa_region is still there)
    with xr.open_dataset(path) as ds_after:
        assert "epa_region" in ds_after.data_vars
        np.testing.assert_array_equal(ds_after["epa_region"].values, [1, 2, 3])

def test_check_for_epa_ecoregions_and_add_if_not_exists_epa_region_missing(tmp_path: Path) -> None:
    # Setup: Create a dataset where 'epa_region' is missing
    # Use real state codes that us_state_to_ecoregion expects
    data_vars = {
        "state": (["x"], ["AL", "NY", "CA"])
    }
    path = _run_check_epa_ecoregions_(tmp_path, data_vars)

    # Verify dataset WAS modified and contains epa_region
    with xr.open_dataset(path) as ds_after:
        assert "epa_region" in ds_after.data_vars
        assert ds_after["epa_region"].attrs["long_name"] == "US EPA ecoregion added by AQM-Eval"
        # AL -> R4, NY -> R2, CA -> R9
        np.testing.assert_array_equal(ds_after["epa_region"].values, ["R4", "R2", "R9"])
