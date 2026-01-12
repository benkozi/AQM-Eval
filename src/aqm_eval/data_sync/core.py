"""Core data synchronization functionality.

Provides context classes and runners for synchronizing UFS-AQM data from S3.
"""

import datetime
import logging
import subprocess
from abc import ABC, abstractmethod
from enum import StrEnum, unique
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import computed_field, model_validator

from aqm_eval.base import AeBaseModel
from aqm_eval.logging_aqm_eval import LOGGER


@unique
class UseCaseKey(StrEnum):
    """Enumeration of available use cases. A "use case" provides a set of pre-defined parameters for data synchronization.

    Attributes
    ----------
    UNDEFINED : str
        Undefined use case. No synchronization parameters are overridden.
    AEROMMA : str
        AEROMMA field campaign use case.
    """

    UNDEFINED = "UNDEFINED"
    AEROMMA = "AEROMMA"


class AbstractContext(ABC, AeBaseModel):
    """Abstract base class for synchronization contexts.

    Attributes
    ----------
    dst_dir : Path
        Destination directory for downloaded data.
    s3_root : str
        Root S3 bucket path.
    max_concurrent_requests : int | None
        Maximum concurrent S3 requests. Higher values will reduce synchronization wall times but be wary of platform constraints.
    dry_run : bool
        Whether to perform a dry run. If `True`, no data is moved.
    """

    dst_dir: Path
    s3_root: str = "s3://noaa-ufs-srw-pds"
    max_concurrent_requests: int | None = 3
    dry_run: bool = False

    @computed_field
    def system_max_concurrent_requests(self) -> int | None:
        """Get system AWS max concurrent requests setting.

        Returns
        -------
        int | None
            System max concurrent requests or None if not retrievable.
        """
        try:
            raw_output = subprocess.check_output(("aws", "configure", "get", "default.s3.max_concurrent_requests"))
        except subprocess.CalledProcessError:
            LOGGER("could not retrieve max_concurrent_requests", level=logging.WARNING)
            return None
        else:
            return int(raw_output)


class SRWFixedContext(AbstractContext):
    """Context for SRW fixed data synchronization.

    Attributes
    ----------
    s3_root : str
        S3 root path for SRW fixed data.
    """

    s3_root: str = "s3://noaa-ufs-srw-pds/develop-20250702"


class ObservationsContext(AbstractContext):
    """Context for observations data synchronization."""

    s3_root: str = "s3://noaa-ufs-srw-pds/UFS-AQM"


class TimeVaryingContext(AbstractContext):
    """Context for time-varying data synchronization.

    Attributes
    ----------
    first_cycle_date : datetime.datetime
        First cycle date for data download.
    fcst_hr : int
        Forecast hour.
    last_cycle_date : datetime.datetime
        Last cycle date for data download.
    s3_root : str
        S3 root path for time-varying data.
    snippet : bool
        Whether to download only a snippet. If `True`, the first time coordinate is synchronized.
    """

    first_cycle_date: datetime.datetime
    fcst_hr: int = 0
    last_cycle_date: datetime.datetime
    s3_root: str = "s3://noaa-ufs-srw-pds/UFS-AQM"
    snippet: bool = False

    @model_validator(mode="before")
    @classmethod
    def _initialize_model_(cls, values: dict) -> dict:
        if values.get("last_cycle_date") is None:
            values["last_cycle_date"] = values["first_cycle_date"]
        for ii in ("first_cycle_date", "last_cycle_date"):
            if isinstance(values[ii], str):
                values[ii] = datetime.datetime.strptime(values[ii], "%Y%m%d%H")
        return values

    @model_validator(mode="after")
    def _finalize_model_(self) -> "TimeVaryingContext":
        if self.last_cycle_date < self.first_cycle_date:
            raise ValueError("last_cycle_date must be >= first_cycle_date")
        return self


class UseCase(TimeVaryingContext):
    """Use case configuration for data synchronization.

    Attributes
    ----------
    key : UseCaseKey
        Use case identifier.
    """

    key: UseCaseKey

    @classmethod
    def from_key(
        cls,
        key: UseCaseKey = UseCaseKey.UNDEFINED,
        **kwargs: Any,
    ) -> "UseCase":
        """Create UseCase instance.

        Parameters
        ----------
        key : UseCaseKey
            Use case identifier.
        **kwargs : Any
            Additional keyword arguments passed to the initializer.

        Returns
        -------
        UseCase
            Configured use case instance.
        """
        match key:
            case UseCaseKey.UNDEFINED:
                instance = cls(key=key, **kwargs)
            case UseCaseKey.AEROMMA:
                instance = UseCaseAeromma(**kwargs)
            case _:
                raise NotImplementedError(key)
        return instance


class UseCaseAeromma(UseCase):
    """AEROMMA field campaign use case configuration.

    Attributes
    ----------
    key : UseCaseKey
        AEROMMA use case identifier.
    first_cycle_date : datetime.datetime
        Campaign start date.
    last_cycle_date : datetime.datetime
        Campaign end date.
    """

    key: UseCaseKey = UseCaseKey.AEROMMA
    first_cycle_date: datetime.datetime = datetime.datetime(2023, 6, 1, hour=12)
    last_cycle_date: datetime.datetime = datetime.datetime(2023, 8, 31, hour=12)

    @model_validator(mode="before")
    @classmethod
    def _initialize_model_(cls, values: dict) -> dict:
        for key in ("first_cycle_date", "last_cycle_date"):
            # Allow values to be initialized by the parent model with empty strings
            if values.get(key, "") is None:
                values.pop(key)
        return values


T = TypeVar("T", bound=AbstractContext)


class AbstractS3SyncRunner(ABC, Generic[T]):
    """Abstract base class for S3 synchronization runners.

    Parameters
    ----------
    T : bound=AbstractContext
        Context type for the sync runner.
    """

    def __init__(self, context: T) -> None:
        """Initialize the abstract runner.

        Parameters
        ----------
        context : T
            Synchronization context.
        """
        self._ctx = context

    def run(self) -> None:
        """Execute the synchronization process."""
        try:
            LOGGER(f"{self._ctx=}")
            self._run_impl_()
        finally:
            self.finalize()

    def finalize(self) -> None:
        """Finalize the synchronization operation and reset system settings."""
        self._handle_max_concurrent_request_reset_()
        LOGGER("success")

    def _run_impl_(self) -> None:
        cmd = self._create_sync_cmd_()
        LOGGER(f"{cmd=}", level=logging.DEBUG)

        if self._ctx.max_concurrent_requests is not None:
            LOGGER("setting max concurrent requests")
            subprocess.check_call(
                [
                    "aws",
                    "configure",
                    "set",
                    "default.s3.max_concurrent_requests",
                    str(self._ctx.max_concurrent_requests),
                ]
            )

        LOGGER("executing sync command")
        subprocess.check_call(cmd)

    def _create_sync_cmd_(self) -> tuple[str, ...]:
        cmd = ["aws", "s3", "sync", "--no-sign-request"]
        if self._ctx.dry_run:
            LOGGER("this is a DRY RUN")
            cmd.append("--dryrun")
        cmd += ["--exclude", "*"]
        self._update_include_templates_(cmd)
        cmd.append(self._ctx.s3_root)
        cmd.append(str(self._ctx.dst_dir))
        return tuple(cmd)

    @abstractmethod
    def _update_include_templates_(self, cmd: list[str]) -> None:
        pass

    def _handle_max_concurrent_request_reset_(self) -> None:
        if self._ctx.system_max_concurrent_requests is not None:
            LOGGER("resetting max_concurrent_requests")
            subprocess.check_call(
                (
                    "aws",
                    "configure",
                    "set",
                    "default.s3.max_concurrent_requests",
                    str(self._ctx.system_max_concurrent_requests),
                )
            )


class SRWFixedSyncRunner(AbstractS3SyncRunner[SRWFixedContext]):
    """Synchronization runner for SRW fixed data."""

    def _update_include_templates_(self, cmd: list[str]) -> None:
        cmd += ["--include", "fix/*", "--include", "NaturalEarth/*"]


class ObservationsSyncRunner(AbstractS3SyncRunner[ObservationsContext]):
    """Synchronization runner for observations data."""

    def _update_include_templates_(self, cmd: list[str]) -> None:
        cmd += ["--include", "Observations/*"]


class TimeVaryingSyncRunner(AbstractS3SyncRunner[TimeVaryingContext]):
    """Synchronization runner for time-varying data."""

    def _update_include_templates_(self, cmd: list[str]) -> None:
        restart_cycle_date = self._ctx.first_cycle_date - datetime.timedelta(days=1)
        curr_cycle_date = self._ctx.first_cycle_date
        ctr = 0
        while True:
            LOGGER(f"{ctr=}, {curr_cycle_date=}")
            if ctr > 1000:
                LOGGER("", exc_info=ValueError(f"{ctr=} - Exceeded max iterations"))
            include_templates = self._create_include_templates_for_cycle_date_(curr_cycle_date)
            if ctr == 0:
                LOGGER("adding restart file download")
                include_templates.append(f"RESTART/*{restart_cycle_date.strftime('%Y%m%d')}*")
            for it in include_templates:
                cmd += ["--include", it]
            if curr_cycle_date == self._ctx.last_cycle_date or (self._ctx.snippet is True and ctr == 1):
                LOGGER("finished adding include filters")
                break
            curr_cycle_date += datetime.timedelta(days=1)
            ctr += 1

    def _create_include_templates_for_cycle_date_(self, curr_cycle_date: datetime.datetime) -> list[str]:
        curr_cycle_date_str = curr_cycle_date.strftime("%Y%m%d")
        include_templates = [
            f"GFS_SFC_DATA/gfs.{curr_cycle_date_str}/12/atmos/gfs.t12z.sfcanl.nc",
            f"FV3GFS/gfs.{curr_cycle_date_str}/12/atmos/gfs.t12z.atmanl.nc",
            f"RAVE_fire/{curr_cycle_date_str}/*.nc",
        ]
        for fhr in range(self._ctx.fcst_hr, self._ctx.fcst_hr + 30, 6):
            include_templates += [
                f"FV3GFS/gfs.{curr_cycle_date_str}/12/atmos/gfs.t{self._ctx.first_cycle_date.hour:02}z.atmf{fhr:03}.nc",
                f"FV3GFS/gfs.{curr_cycle_date_str}/12/atmos/gfs.t{self._ctx.first_cycle_date.hour:02}z.sfcf{fhr:03}.nc",
                f"GFS_SFC_DATA/gfs.{curr_cycle_date_str}/12/atmos/gfs.t12z.sfcf{fhr:03}.nc",
            ]
        for fhr in [3, 9, 15, 21]:
            include_templates += [
                f"GFS_SFC_DATA/gfs.{curr_cycle_date_str}/12/atmos/gfs.t12z.sfcf{fhr:03}.nc",
            ]
        for fhr in range(self._ctx.fcst_hr, self._ctx.fcst_hr + 42, 6):
            include_templates += [f"GEFS_Aerosol/{curr_cycle_date_str}/00/gfs.t00z.atmf{fhr:03}.nemsio"]
        return include_templates
