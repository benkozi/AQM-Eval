from functools import cached_property

from pydantic import computed_field

from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.package.core import AbstractEvalPackage, PackageKey, TaskKey


class AQS_VOC_EvalPackage(AbstractEvalPackage):
    """Defines a AQS VOC evaluation package."""

    key: PackageKey = PackageKey.AQS_VOC
    namelist_template: str = "namelist.aqs.voc.j2"

    @computed_field(description="Tasks that the package will run.")
    @cached_property
    def tasks(self) -> tuple[TaskKey, ...]:
        return (
            TaskKey.SAVE_PAIRED,
            TaskKey.TIMESERIES,
            TaskKey.TAYLOR,
            TaskKey.SPATIAL_BIAS,
            TaskKey.SPATIAL_OVERLAY,
            TaskKey.BOXPLOT,
            TaskKey.MULTI_BOXPLOT,
            TaskKey.CSI,
            TaskKey.STATS,
        )

    @log_it
    def initialize(self) -> None:
        super().initialize()
        for model in self.mm_models:
            model.create_symlinks()
