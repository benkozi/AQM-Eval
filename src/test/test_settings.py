import os

from aqm_eval.settings import SETTINGS


def test() -> None:
    print(SETTINGS)
    print(os.environ)
    assert SETTINGS.slurm_nnodes is not None
    assert SETTINGS.slurm_ntasks_per_node is not None
