import os
import re
import datetime
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from aqm_eval.mm_eval.driver.config import PackageKey
from pydantic import BaseModel, computed_field
import shutil


class StatsFile(BaseModel):
    model_config = {"frozen": True}

    variable: str
    region_type: str
    region_id: str
    start_date: datetime.datetime
    end_date: datetime.datetime
    package_key: PackageKey | None = None
    path: Path

    @classmethod
    def from_path(cls, path: Path, package_key: PackageKey | None = None) -> "StatsFile":
        pattern = re.compile("stats\.(?P<variable>.+)\.(?P<region_type>all|epa_region)\.(?P<region_id>.+)\.(?P<start_date>[0-9-_]+)\.(?P<end_date>[0-9-_]+)\.csv")
        match = re.match(pattern, path.name)
        data = match.groupdict()
        data["path"] = path
        data["start_date"] = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d_%H")
        data["end_date"] = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d_%H")
        data["package_key"] = package_key
        return cls.model_validate(data)

    def as_dataframe(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        id_vars = ("Stat_ID", "Stat_FullName")
        value_vars = set(df.columns) - set(id_vars)
        df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name="model", value_name="value")
        for k, v in self.model_dump().items():
            df[k] = v
        return df

class StatsFileCollection(BaseModel):
    model_config = {"frozen": True}

    stats_files: tuple[StatsFile, ...]
    index_name: str = "id"
    created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

    @classmethod
    def from_dir(cls, path: Path) -> "StatsFileCollection":
        stats_files = []
        for path in path.rglob("**/stats.*.csv"):
            package_key = None
            for ii in PackageKey:
                if ii.value in path.parts:
                    package_key = ii
                    break
            sfile = StatsFile.from_path(path, package_key=package_key)
            stats_files.append(sfile)
        return cls(stats_files=stats_files)

    def as_dataframe(self) -> pd.DataFrame:
        dfs = [sfile.as_dataframe() for sfile in self.stats_files]
        for df in dfs:
            df["created_at"] = self.created_at
        ret = pd.concat(dfs, ignore_index=True)
        ret.index.name = self.index_name
        return ret


@pytest.fixture
def mm_filenames() -> tuple[str, ...]:
    return ("stats.TOLUENE.all.CONUS.2023-08-01_12.2023-08-31_12.csv",
            "stats.PROPANE.epa_region.R1.2023-08-01_12.2023-08-31_12.csv")

def test_as_dataframe(tmp_path: Path, bin_dir: Path, mm_filenames: tuple[str, ...]) -> None:
    stats_files = []
    for fn in mm_filenames:
        dst = tmp_path / fn
        shutil.copy2(bin_dir / "example-mm-stats.csv", dst)
        sfile = StatsFile.from_path(dst, package_key=PackageKey.CHEM)
        stats_files.append(sfile)
    sfile_coll = StatsFileCollection(stats_files=stats_files)

    df = sfile_coll.as_dataframe()

    out_path = tmp_path / "out.csv"
    df.to_csv(out_path)
    out_df = pd.read_csv(out_path)

    # print(out_df)
    # os.startfile(str(out_path))

    assert len(out_df) == 48
    assert out_df.columns.tolist() == ['id', 'Stat_ID', 'Stat_FullName', 'model', 'value', 'variable', 'region_type', 'region_id', 'start_date', 'end_date', 'package_key', 'path', 'created_at']


def test_from_dir(tmp_path: Path, bin_dir: Path, mm_filenames: tuple[str, ...]) -> None:
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

    assert len(out_df) == 48 * len(PackageKey)
    expected_package_key = set([ii.value for ii in PackageKey])
    assert set(out_df.package_key.unique()) == expected_package_key
    for ii in out_df["package_key"].tolist():
        assert ii in expected_package_key