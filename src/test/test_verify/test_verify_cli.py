from pathlib import Path

import yaml
from typer.testing import CliRunner

from aqm_eval.verify.context import VerifyContext
from aqm_eval.verify.verify_cli import app


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"], catch_exceptions=False)
    print(result.output)
    assert result.exit_code == 0


def test_happy_path(verify_ctx: VerifyContext, tmp_path: Path) -> None:
    yaml_data = {"aqm-verify": verify_ctx.model_dump(mode="json")}
    yaml_path = tmp_path / "verify.yaml"
    yaml_path.write_text(yaml.safe_dump(yaml_data))
    print(yaml.safe_dump(yaml_data, sort_keys=False))

    runner = CliRunner()
    result = runner.invoke(app, ["--yaml-path", str(yaml_path)], catch_exceptions=False)
    print(result.output)
    assert result.exit_code == 0
