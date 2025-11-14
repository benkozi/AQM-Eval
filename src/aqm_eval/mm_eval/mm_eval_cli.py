"""The CLI definition for the MELODIES MONET UFS-AQM evaluation suite."""

import os
from pathlib import Path

import typer

from aqm_eval.mm_eval.driver.config import PackageKey, TaskKey
from aqm_eval.mm_eval.driver.package.core import package_key_to_class
from aqm_eval.mm_eval.rocoto.srw_task_group import srw_data_to_json
from aqm_eval.mm_eval.stats_concat import StatsFileCollection

os.environ["NO_COLOR"] = "1"
app = typer.Typer(pretty_exceptions_enable=False)


@app.command(
    name="srw-init",
    help="Initialize the MELODIES MONET UFS-AQM evaluation from the SRW workflow.",
)
def srw_init(
    expt_dir: Path = typer.Option(..., "--expt-dir", help="Experiment directory."),
    package_selector: PackageKey = typer.Option(..., "--package", help="Package selector."),
) -> None:
    from aqm_eval.mm_eval.driver.context.srw import SRWContext

    ctx = SRWContext.from_expt_dir(expt_dir)
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

    ctx = SRWContext.from_expt_dir(expt_dir)
    klass = package_key_to_class(package_selector)
    package = klass.model_validate(dict(ctx=ctx))
    package.run(task_key=task_selector)


@app.command(
    name="srw-task-group",
    help="Create a YAML-based SRW task group for all packages and tasks.",
)
def srw_task_group(
    srw_data: str = typer.Option(..., "--srw-data"),
) -> None:
    srw_data_to_json(srw_data)


@app.command(
    name="concat-stats",
    help="Concatenate MM stats files from all packages and tasks into a single CSV file.",
)
def concat_stats(
    root_dir: Path = typer.Option(..., "--root-dir", help="Root directory containing MM stats files.", file_okay=False),
    out_path: Path = typer.Option(
        ..., "--out-path", help="Output path for the concatenated CSV file.", exists=False, dir_okay=False
    ),
) -> None:
    # tdk:doc
    sfile_coll = StatsFileCollection.from_dir(root_dir)
    df = sfile_coll.as_dataframe()
    df.to_csv(out_path)


if __name__ == "__main__":
    app()
