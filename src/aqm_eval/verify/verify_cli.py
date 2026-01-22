import json
import os
from pathlib import Path

import typer

from aqm_eval.verify.context import VerifyContext
from aqm_eval.verify.runner import run_verify

os.environ["NO_COLOR"] = "1"
app = typer.Typer(pretty_exceptions_enable=False)


@app.command(
    help="Verify UFS-AQM output using nccmp.",
)
def aqm_verify(
    json_data: str = typer.Option(..., "--json-data")
) -> None:
    ctx = VerifyContext.model_validate(json.loads(json_data))
    run_verify(ctx)


if __name__ == "__main__":
    app()
