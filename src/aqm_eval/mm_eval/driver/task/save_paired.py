from pathlib import Path

from pydantic import model_validator

from aqm_eval.base import AeBaseModel


class SavePaired(AeBaseModel):
    method: str
    predix: str | None
    data: str


class Save(AeBaseModel):
    paired: SavePaired


class ReadPaired(AeBaseModel):
    method: str
    filenames: dict[str, str]


class Read(AeBaseModel):
    paired: ReadPaired


class Analysis(AeBaseModel):
    start_time: str  # yyyy-mm-dd-HH:MM:SS UTC
    end_time: str  # yyyy-mm-dd-HH:MM:SS UTC
    output_dir: Path
    debug: bool
    save: Save | None
    read: Read | None

    @model_validator(mode="after")
    def _validate_(self) -> "Analysis":
        if self.save is None and self.read is None:
            raise ValueError("Either save or read must be set.")
        if self.save is not None and self.read is not None:
            raise ValueError("Only one of save or read can be set.")
        return self


class SavePairedTask(AeBaseModel):
    analysis: Analysis

    def to_yaml(self) -> dict:
        return self.model_dump(mode="json")
