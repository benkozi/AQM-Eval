from pathlib import Path

import pytest

from aqm_eval.shared import assert_directory_exists, assert_file_exists, calc_2d_chunks


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
