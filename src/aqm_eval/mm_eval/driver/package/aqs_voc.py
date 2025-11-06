from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.package.core import AbstractEvalPackage


class AQS_VOC_EvalPackage(AbstractEvalPackage):
    """Defines a AQS VOC evaluation package."""

    key: PackageKey = PackageKey.AQS_VOC
    namelist_template: str = "namelist.aqs.voc.j2"
    tasks_default: tuple[TaskKey, ...] = (
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
