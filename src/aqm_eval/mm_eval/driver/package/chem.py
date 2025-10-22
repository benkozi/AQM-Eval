from aqm_eval.logging_aqm_eval import log_it
from aqm_eval.mm_eval.driver.package.core import AbstractEvalPackage, PackageKey, TaskKey


class ChemEvalPackage(AbstractEvalPackage):
    """Defines a chemistry evaluation package."""

    key: PackageKey = PackageKey.CHEM
    namelist_template: str = "namelist.chem.j2"
    tasks_default: tuple[TaskKey, ...] = tuple(TaskKey)

    @log_it
    def initialize(self) -> None:
        super().initialize()
        for model in self.mm_models:
            model.create_symlinks()
