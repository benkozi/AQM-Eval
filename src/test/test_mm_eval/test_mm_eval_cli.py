from pathlib import Path

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.driver.package.core import AbstractEvalPackage
from aqm_eval.mm_eval.mm_eval_cli import app
from aqm_eval.mm_eval.rocoto.srw_task_group import cli_arg_to_json, json_to_cli_arg


def test_help() -> None:
    """Test that the help message can be displayed."""
    runner = CliRunner()
    for subcommand in ("srw-init", "srw-run", "srw-task-group", "concat-stats"):
        result = runner.invoke(app, [subcommand, "--help"], catch_exceptions=False)
        print(result.output)
        assert result.exit_code == 0


def test_srw_run_package_and_task_selector(tmp_path: Path, srw_context: SRWContext, mocker: MockerFixture) -> None:
    mock_run = mocker.patch.object(AbstractEvalPackage, "run")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "srw-run",
            "--expt-dir",
            str(srw_context.expt_dir),
            "--task",
            "save_paired",
            "--package",
            "chem",
        ],
        catch_exceptions=False,
    )
    print(result.output)
    assert result.exit_code == 0
    mock_run.assert_called_once()


def test_srw_task_group(srw_context: SRWContext) -> None:
    srw_data = json_to_cli_arg(srw_context.model_dump(mode="json"))
    runner = CliRunner()
    result = runner.invoke(app, ["srw-task-group", "--srw-data", srw_data])
    tg = cli_arg_to_json(result.output)
    assert isinstance(tg, dict)
    assert result.exit_code == 0
