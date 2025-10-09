"""Defines the MM evaluation runner to initialize, run, and finalize a configuration."""
from functools import cached_property

import cartopy  # type: ignore[import-untyped]
import dask
import matplotlib
from melodies_monet import driver  # type: ignore[import-untyped]
from melodies_monet.driver import analysis  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from aqm_eval.logging_aqm_eval import LOGGER, log_it
from aqm_eval.mm_eval.driver.context.base import AbstractDriverContext
from aqm_eval.mm_eval.driver.package import PackageKey, TaskKey, AbstractEvalPackage


class MMEvalRunner(BaseModel):
    """Initialize, run, and finalize an MM evaluation.

    Parameters
    ----------
    package_selector: tuple[PackageKey, ...] = tuple(PackageKey), optional
        Optionally select packages to run. Used to limit packages that may already be configured.
    task_selector: tuple[TaskKey, ...] = tuple(TaskKey), optional
        Optionally select tasks to run. Used to limit tasks that may already be configured.
    """

    model_config = {"frozen": True}

    ctx: AbstractDriverContext = Field(description="Driver context.")
    #tdk: runner should only be for one package and task?
    package_key: PackageKey = Field(description="MM package key to run.")

    @log_it
    def initialize(self) -> None:
        """Initialize the runner. Create symlinks and control files for example.

        Returns
        -------
        None
        """
        LOGGER(f"{self.ctx=}")
        LOGGER(f"{self.package_key=}")

        # Only create symlinks once for each model
        #tdk:last: move to package
        assert not self.package_to_run.run_dir.exists()
        assert not self.package_to_run.mm_package_output_dir.exists()
        assert not self.package_to_run.mm_models[0].link_alldays_path.exists()
        for model in self.package_to_run.mm_models:
            model.create_symlinks()

        LOGGER("creating MM control configs")
        #tdk:last: move to package
        self.package_to_run.create_control_configs(self.ctx)

        LOGGER("initializing package")
        self.package_to_run.initialize()

    @cached_property
    def package_to_run(self) -> AbstractEvalPackage:
        package_to_run = None
        for package in self.ctx.mm_packages:
            if package.key == self.package_key:
                package_to_run = package
                break
        if package_to_run is None:
            raise ValueError
        assert isinstance(package_to_run, AbstractEvalPackage)
        return package_to_run

    @log_it
    def run(
        self,
        task_key: TaskKey, #tdk: doc
        finalize: bool = False,
    ) -> None:
        """Run the MM evaluation.

        finalize: bool = False, optional
            If True, finalize the runner after the run completes, successfully or not.

        Returns
        -------
        None
        """
        LOGGER(f"{task_key=}")
        LOGGER(f"{finalize=}")

        assert self.package_to_run.run_dir.exists()
        assert not self.package_to_run.mm_package_output_dir.exists()

        try:
            matplotlib.use("Agg")
            cartopy.config["data_dir"] = self.ctx.cartopy_data_dir
            dask.config.set({"array.slicing.split_large_chunks": True})
            an = driver.analysis()
            control_yaml = self.ctx.mm_run_dir / self.package_to_run.key.value / f"control_{task_key.value}.yaml"
            LOGGER(f"{control_yaml=}")
            an.control = control_yaml
            an.read_control()

            self._run_task_(an, task_key)
        finally:
            if finalize:
                self.finalize()

    @staticmethod
    @log_it
    def _run_task_(an: analysis, task: TaskKey) -> None:
        match task:
            case TaskKey.SAVE_PAIRED:
                an.open_models()
                an.open_obs()
                an.pair_data()
                an.save_analysis()
            case TaskKey.SPATIAL_OVERLAY | TaskKey.SPATIAL_BIAS:
                an.read_analysis()
                an.open_models()
                an.plotting()
            case TaskKey.STATS:
                an.read_analysis()
                an.stats()
            case _:
                an.read_analysis()
                an.plotting()

    @log_it
    def finalize(self) -> None:
        """Finalize the runner.

        Returns
        -------
        None
        """
        ...
