"""The CLI definition for the MELODIES MONET UFS-AQM evaluation suite."""

import os
from pathlib import Path

import typer

from aqm_eval.mm_eval.driver.context.yaml_eval import YAMLContext
from aqm_eval.mm_eval.driver.package import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.runner import MMEvalRunner

os.environ["NO_COLOR"] = "1"
app = typer.Typer(pretty_exceptions_enable=False)


@app.command(
    name="yaml-init",
    help="Initialize the MELODIES MONET UFS-AQM evaluation from a pure YAML file.",
)
def yaml_init(yaml_config: Path = typer.Option(..., "--yaml-config", help="The evaluation's YAML configuration.")) -> None:
    ctx = YAMLContext(yaml_config=yaml_config)
    runner = MMEvalRunner(ctx=ctx)
    runner.initialize()


@app.command(
    name="yaml-run",
    help="Run the MELODIES MONET UFS-AQM evaluation using a pure YAML file.",
)
def yaml_run(yaml_config: Path = typer.Option(..., "--yaml-config", help="The evaluation's YAML configuration.")) -> None:
    ctx = YAMLContext(yaml_config=yaml_config)
    runner = MMEvalRunner(ctx=ctx)
    runner.run()


@app.command(
    name="srw-init",
    help="Initialize the MELODIES MONET UFS-AQM evaluation from the SRW workflow.",
)
def srw_init(
    expt_dir: Path = typer.Option(..., "--expt-dir", help="Experiment directory."),
    package_selector: list[PackageKey] = typer.Option(list(PackageKey), "--package-selector", help="Package selector."),
    task_selector: list[TaskKey] = typer.Option(list(TaskKey), "--task-selector", help="Task selector."),
) -> None:
    from aqm_eval.mm_eval.driver.context.srw import SRWContext

    ctx = SRWContext(expt_dir=expt_dir)
    runner = MMEvalRunner(ctx=ctx, task_selector=tuple(task_selector), package_selector=tuple(package_selector))
    runner.initialize()


@app.command(
    name="srw-run",
    help="Run the MELODIES MONET UFS-AQM evaluation from the SRW workflow.",
)
def srw_run(
    expt_dir: Path = typer.Option(..., "--expt-dir", help="Experiment directory."),
    package_selector: list[PackageKey] = typer.Option(list(PackageKey), "--package-selector", help="Package selector."),
    task_selector: list[TaskKey] = typer.Option(list(TaskKey), "--task-selector", help="Task selector."),
) -> None:
    from aqm_eval.mm_eval.driver.context.srw import SRWContext

    ctx = SRWContext(expt_dir=expt_dir)
    runner = MMEvalRunner(ctx=ctx, task_selector=tuple(task_selector), package_selector=tuple(package_selector))
    runner.run()


if __name__ == "__main__":
    app()
