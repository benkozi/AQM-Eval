from pathlib import Path

from aqm_eval.mm_eval.rocoto.srw_render import render_task_group


def test(tmp_path: Path) -> None:
    render_task_group(tmp_path)
