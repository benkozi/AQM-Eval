import datetime
import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, field_validator

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.config import PackageKey


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
        pattern = re.compile(
            "stats\.(?P<variable>.+)\.(?P<region_type>all|epa_region|country)\.(?P<region_id>.+)\.(?P<start_date>[0-9-_]+)\.(?P<end_date>[0-9-_]+)\.csv"
        )
        match = re.match(pattern, path.name)
        if match is None:
            raise ValueError
        data = match.groupdict()
        data["path"] = path
        data["start_date"] = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d_%H")
        data["end_date"] = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d_%H")
        data["package_key"] = package_key
        return cls.model_validate(data)

    def as_dataframe(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        id_vars = ("Stat_ID", "Stat_FullName")
        value_vars = tuple(set(df.columns) - set(id_vars))
        df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name="model", value_name="value")
        for k, v in self.model_dump().items():
            df[k] = v
        return df

    @field_validator("path", mode="before")
    @classmethod
    def _validate_path_(cls, value: Path) -> Path:
        return value.absolute().resolve(strict=True)


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
            LOGGER(f"parsing {path=}, {package_key=}")
            sfile = StatsFile.from_path(path, package_key=package_key)
            LOGGER(f"found stats file: {sfile}")
            stats_files.append(sfile)
        return cls(stats_files=tuple(stats_files))

    def as_dataframe(self) -> pd.DataFrame:
        dfs = [sfile.as_dataframe() for sfile in self.stats_files]
        for df in dfs:
            df["created_at"] = self.created_at
        ret = pd.concat(dfs, ignore_index=True)
        ret.index.name = self.index_name
        return ret
