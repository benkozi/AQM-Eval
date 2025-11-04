import os
import re
import datetime
import subprocess
from pathlib import Path

import pandas as pd
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

    def as_dataframe(self) -> pd.DataFrame:
        dfs = [sfile.as_dataframe() for sfile in self.stats_files]
        ret = pd.concat(dfs, ignore_index=True)
        ret.index.name = self.index_name
        return ret

def test(tmp_path: Path, bin_dir: Path) -> None:
    fns = ("stats.TOLUENE.all.CONUS.2023-08-01_12.2023-08-31_12.csv",
           "stats.PROPANE.epa_region.R1.2023-08-01_12.2023-08-31_12.csv")

    stats_files = []
    for fn in fns:
        dst = tmp_path / fn
        shutil.copy2(bin_dir / "example-mm-stats.csv", dst)
        sfile = StatsFile.from_path(dst, package_key=PackageKey.CHEM)
        stats_files.append(sfile)
    sfile_coll = StatsFileCollection(stats_files=stats_files)

    df = sfile_coll.as_dataframe()

    out_path = tmp_path / "out.csv"
    df.to_csv(out_path)
    out_df = pd.read_csv(out_path)
    print(out_df)
    os.startfile(str(out_path))
