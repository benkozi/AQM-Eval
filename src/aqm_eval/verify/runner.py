import subprocess

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.verify.context import VerifyContext


def run_verify(ctx: VerifyContext) -> None:
    for cmd in ctx.iter_nccmp_cmds():
        LOGGER(cmd)
        subprocess.check_call(cmd)