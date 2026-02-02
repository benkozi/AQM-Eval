import os
from pathlib import Path

import typer
import yaml

from aqm_eval.verify.context import VerifyContext
from aqm_eval.verify.runner import run_verify

os.environ["NO_COLOR"] = "1"
app = typer.Typer(pretty_exceptions_enable=False)


@app.command(
    help="Verify UFS-AQM output using nccmp.",
)
def aqm_verify(
    yaml_path: Path = typer.Option(
        ..., "--yaml-path", help="Path to YAML file containing the configuration's root key", exists=True, dir_okay=False
    ),
    root_key: str = typer.Option(
        "aqm-verify", "--root-key", help="If provided, use this key when extracting the root configuration"
    ),
) -> None:
    yaml_data = yaml.safe_load(yaml_path.read_text())
    ctx = VerifyContext.model_validate(yaml_data[root_key])
    run_verify(ctx)


if __name__ == "__main__":
    app()
