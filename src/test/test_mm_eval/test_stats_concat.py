import shutil
from pathlib import Path

import pandas as pd
import pytest

from aqm_eval.mm_eval.driver.config import PackageKey
from aqm_eval.mm_eval.stats_concat import StatsFile, StatsFileCollection


@pytest.fixture
def mm_filenames() -> tuple[str, ...]:
    return (
        "stats.TOLUENE.all.CONUS.2023-08-01_12.2023-08-31_12.csv",
        "stats.PROPANE.epa_region.R1.2023-08-01_12.2023-08-31_12.csv",
        "stats.dew_pt_temp.country.US.2023-08-01_12.2023-08-31_12.csv",
    )


@pytest.fixture
def expected_n_rows(mm_filenames: tuple[str, ...]) -> int:
    return len(mm_filenames) * 24


def test_as_dataframe(tmp_path: Path, bin_dir: Path, mm_filenames: tuple[str, ...], expected_n_rows: int) -> None:
    stats_files = []
    for fn in mm_filenames:
        dst = tmp_path / fn
        shutil.copy2(bin_dir / "example-mm-stats.csv", dst)
        sfile = StatsFile.from_path(dst, package_key=PackageKey.CHEM)
        stats_files.append(sfile)
    sfile_coll = StatsFileCollection(stats_files=tuple(stats_files))

    df = sfile_coll.as_dataframe()

    out_path = tmp_path / "out.csv"
    df.to_csv(out_path)
    out_df = pd.read_csv(out_path)

    # print(out_df)
    # os.startfile(str(out_path))

    assert len(out_df) == expected_n_rows
    assert out_df.columns.tolist() == [
        "id",
        "Stat_ID",
        "Stat_FullName",
        "model",
        "value",
        "variable",
        "region_type",
        "region_id",
        "start_date",
        "end_date",
        "package_key",
        "path",
        "created_at",
    ]


def test_from_dir(tmp_path: Path, bin_dir: Path, mm_filenames: tuple[str, ...], expected_n_rows: int) -> None:
    for package_key in PackageKey:
        out_dir = tmp_path / package_key.value
        out_dir.mkdir()
        for fn in mm_filenames:
            dst = out_dir / fn
            shutil.copy2(bin_dir / "example-mm-stats.csv", dst)

    sfile_coll = StatsFileCollection.from_dir(tmp_path)
    df = sfile_coll.as_dataframe()

    out_path = tmp_path / "out.csv"
    df.to_csv(out_path)
    out_df = pd.read_csv(out_path)

    # print(out_df)
    # os.startfile(str(out_path))

    assert len(out_df) == expected_n_rows * len(PackageKey)
    expected_package_key = set([ii.value for ii in PackageKey])
    assert set(out_df.package_key.unique()) == expected_package_key
    for ii in out_df["package_key"].tolist():
        assert ii in expected_package_key
