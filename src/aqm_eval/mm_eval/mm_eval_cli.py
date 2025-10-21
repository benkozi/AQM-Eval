"""The CLI definition for the MELODIES MONET UFS-AQM evaluation suite."""

import os
from pathlib import Path

import typer

from aqm_eval.mm_eval.driver.context.yaml_eval import YAMLContext
from aqm_eval.mm_eval.driver.package.core import PackageKey, TaskKey, package_key_to_class

os.environ["NO_COLOR"] = "1"
app = typer.Typer(pretty_exceptions_enable=False)


@app.command(
    name="yaml-init",
    help="Initialize the MELODIES MONET UFS-AQM evaluation from a pure YAML file.",
)
def yaml_init(yaml_config: Path = typer.Option(..., "--yaml-config", help="The evaluation's YAML configuration.")) -> None:
    ctx = YAMLContext(yaml_config=yaml_config)
    klass = package_key_to_class(ctx.mm_package_key)
    package = klass.model_validate(dict(ctx=ctx))
    package.initialize()


@app.command(
    name="yaml-run",
    help="Run the MELODIES MONET UFS-AQM evaluation using a pure YAML file.",
)
def yaml_run(
    yaml_config: Path = typer.Option(..., "--yaml-config", help="The evaluation's YAML configuration."),
    task_selector: TaskKey = typer.Option(..., "--task", help="Task selector."),
) -> None:
    ctx = YAMLContext(yaml_config=yaml_config)
    klass = package_key_to_class(ctx.mm_package_key)
    package = klass.model_validate(dict(ctx=ctx))
    package.run(task_key=task_selector)


@app.command(
    name="srw-init",
    help="Initialize the MELODIES MONET UFS-AQM evaluation from the SRW workflow.",
)
def srw_init(
    expt_dir: Path = typer.Option(..., "--expt-dir", help="Experiment directory."),
    package_selector: PackageKey = typer.Option(..., "--package", help="Package selector."),
) -> None:
    from aqm_eval.mm_eval.driver.context.srw import SRWContext

    ctx = SRWContext(expt_dir=expt_dir)
    klass = package_key_to_class(package_selector)
    package = klass.model_validate(dict(ctx=ctx))
    package.initialize()


@app.command(
    name="srw-run",
    help="Run the MELODIES MONET UFS-AQM evaluation from the SRW workflow.",
)
def srw_run(
    expt_dir: Path = typer.Option(..., "--expt-dir", help="Experiment directory."),
    package_selector: PackageKey = typer.Option(..., "--package", help="Package selector."),
    task_selector: TaskKey = typer.Option(..., "--task", help="Task selector."),
) -> None:
    from aqm_eval.mm_eval.driver.context.srw import SRWContext

    ctx = SRWContext(expt_dir=expt_dir)
    klass = package_key_to_class(package_selector)
    package = klass.model_validate(dict(ctx=ctx))
    package.run(task_key=task_selector)


if __name__ == "__main__":
    app()
