import json

from typer.testing import CliRunner

from aqm_eval.verify.context import VerifyContext
from aqm_eval.verify.verify_cli import app


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"], catch_exceptions=False)
    print(result.output)
    assert result.exit_code == 0


def test_happy_path(verify_ctx: VerifyContext) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--json-data", verify_ctx.model_dump_json()], catch_exceptions=False)
    print(result.output)
    assert result.exit_code == 0