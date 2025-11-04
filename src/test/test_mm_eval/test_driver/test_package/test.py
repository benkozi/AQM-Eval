import re
import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel
import shutil


class StatsFile(BaseModel):
    model_config = {"frozen": True}

    variable: str
    region_type: str
    region_id: str
    start_date: datetime.datetime
    end_date: datetime.datetime
    path: Path

    @classmethod
    def from_path(cls, path: Path) -> "StatsFile":
        pattern = re.compile("stats\.(?P<variable>.+)\.(?P<region_type>all|epa_region)\.(?P<region_id>.+)\.(?P<start_date>[0-9-_]+)\.(?P<end_date>[0-9-_]+)\.csv")
        match = re.match(pattern, path.name)
        data = match.groupdict()
        data["path"] = path
        data["start_date"] = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d_%H")
        data["end_date"] = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d_%H")
        return cls.model_validate(data)

    def as_dataframe(self) -> pd.DataFrame:
        return pd.read_csv(self.path)

def test(tmp_path: Path, bin_dir: Path) -> None:
    fns = ("stats.TOLUENE.all.CONUS.2023-08-01_12.2023-08-31_12.csv",
           "stats.PROPANE.epa_region.R1.2023-08-01_12.2023-08-31_12.csv")
    for fn in fns:
        dst = tmp_path / fn
        shutil.copy2(bin_dir / "example-mm-stats.csv", dst)
        sfile = StatsFile.from_path(dst)
        print(sfile)
        df = sfile.as_dataframe()
        print(df)
