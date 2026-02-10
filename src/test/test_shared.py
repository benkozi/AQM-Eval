from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from aqm_eval.shared import assert_directory_exists, assert_file_exists, calc_2d_chunks, us_state_to_ecoregion


def test_assert_file_exists_with_valid_file(tmp_path: Path) -> None:
    test_file = tmp_path / "test_file.txt"
    test_file.touch()

    result = assert_file_exists(test_file)
    assert result == test_file
    assert result.is_file()


def test_assert_file_exists_with_nonexistent_path(tmp_path: Path) -> None:
    nonexistent_file = tmp_path / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        assert_file_exists(nonexistent_file)


def test_assert_file_exists_with_directory(tmp_path: Path) -> None:
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Should raise ValueError because it's not a file
    with pytest.raises(ValueError, match="path is not a file"):
        assert_file_exists(test_dir)


def test_assert_directory_exists_with_valid_directory(tmp_path: Path) -> None:
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    result = assert_directory_exists(test_dir)
    assert result == test_dir
    assert result.is_dir()


def test_assert_directory_exists_with_nonexistent_path(tmp_path: Path) -> None:
    nonexistent_dir = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError):
        assert_directory_exists(nonexistent_dir)


def test_assert_directory_exists_with_directory(tmp_path: Path) -> None:
    test_file = tmp_path / "test_file.txt"
    test_file.touch()

    # Should raise ValueError because it's not a directory
    with pytest.raises(ValueError, match="path is not a directory"):
        assert_directory_exists(test_file)


def test_calc_2d_chunks() -> None:
    dims = {"y": 20, "x": 10}
    n_chunks = 2
    chunks = calc_2d_chunks(dims, n_chunks)
    assert chunks == {"y": 10, "x": 5}


def test_us_state_to_ecoregion() -> None:
    # Test with shape (y: 1, x: 2719) matching real data structure
    n_stations = 2719
    
    # Create sample state data with variety of states from different regions
    states_sample = ["CA", "NY", "TX", "MA", "WA", "FL", "IL", "CO", "AZ", "OR"]
    states = np.random.choice(states_sample, size=n_stations)
    
    # Create DataArray with proper shape
    da = xr.DataArray(
        states.reshape(1, n_stations),
        dims=["y", "x"],
        name="state"
    )
    
    result = us_state_to_ecoregion(da)
    
    # Verify shape and dimensions are preserved
    assert result.shape == (1, n_stations)
    assert result.dims == ("y", "x")
    
    # Verify mapping for known states in first row
    expected_mapping = {
        "CA": "R9", "NY": "R2", "TX": "R6", "MA": "R1", "WA": "R10",
        "FL": "R4", "IL": "R5", "CO": "R8", "AZ": "R9", "OR": "R10"
    }
    for i in range(n_stations):
        state = states[i]
        expected_region = expected_mapping[state]
        assert result.values[0, i] == expected_region


def test_us_state_to_ecoregion_with_unknown_state() -> None:
    # Test with an unknown state code
    states = np.array(["CA", "XX"])
    da = xr.DataArray(states, dims=["location"])
    result = us_state_to_ecoregion(da)
    
    assert result.values[0] == "R9"
    assert result.values[1] is ""
