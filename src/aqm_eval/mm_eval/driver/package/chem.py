from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.package.core import AbstractEvalPackage


class ChemEvalPackage(AbstractEvalPackage):
    """Defines a chemistry evaluation package."""

    key: PackageKey = PackageKey.CHEM
    observations_title: str = "AirNow"
    observations_label: str = "airnow"
    tasks_default: tuple[TaskKey, ...] = tuple(TaskKey)

    @log_it
    def initialize(self) -> None:
        super().initialize()
        for model in self.mm_models:
            model.create_symlinks()
