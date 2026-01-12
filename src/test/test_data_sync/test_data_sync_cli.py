from pathlib import Path

from pydantic import BaseModel
from typer.testing import CliRunner

from aqm_eval.data_sync.core import UseCaseKey
from aqm_eval.data_sync.data_sync_cli import app


def test_help() -> None:
    """
    Test that the help message can be displayed. Test is also used to generate markdown
    documentation.
    """

    class SubcommandSpec(BaseModel):
        cmd: str
        help_text: str

        @property
        def doc_text(self) -> str:
            fixed_up = self.help_text.replace("Usage: root", "aqm-eval data-sync")
            fixed_up = fixed_up.strip()
            return self.header + "\n" + "```\n" + fixed_up + "\n```\n"

        @property
        def header(self) -> str:
            match self.cmd:
                case "time-varying":
                    ret = "Download time-varying UFS-SRW inputs"
                case "srw-fixed":
                    ret = "Download UFS-SRW fix data"
                case "observations":
                    ret = "Download MELODIES-MONET observations"
                case _:
                    raise NotImplementedError(f"Unknown subcommand {self.cmd}")
            return "## " + ret

    runner = CliRunner()
    for subcommand in ("time-varying", "srw-fixed", "observations"):
        result = runner.invoke(app, [subcommand, "--help"], catch_exceptions=False)
        spec = SubcommandSpec(cmd=subcommand, help_text=result.output)
        print(spec.doc_text)
        assert result.exit_code == 0


def test_time_varying_use_case(tmp_path: Path) -> None:
    """Test the use case pathway for a snippet."""
    runner = CliRunner()

    args = [
        "time-varying",
        "--use-case",
        UseCaseKey.AEROMMA.value,
        "--dst-dir",
        str(tmp_path),
        "--dry-run",
        "--snippet",
    ]
    result = runner.invoke(app, args, catch_exceptions=False)
    print(result.output)
    assert result.exit_code == 0


def test_observations(tmp_path: Path) -> None:
    """Test downloading observations with a dry run."""
    runner = CliRunner()

    args = [
        "observations",
        "--dst-dir",
        str(tmp_path),
        "--dry-run",
    ]
    result = runner.invoke(app, args, catch_exceptions=False)
    print(result.output)
    assert result.exit_code == 0
