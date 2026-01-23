import logging
import subprocess

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.verify.context import VerifyContext


class NccmpError(Exception): ...


def run_verify(ctx: VerifyContext) -> None:
    LOGGER(ctx.model_dump_json())
    error_ctr = 0
    for cmd in ctx.iter_nccmp_cmds():
        LOGGER(str(cmd))
        try:
            subprocess.check_call(cmd)
            LOGGER("verify successful")
        except subprocess.CalledProcessError:
            error_ctr += 1
            if ctx.fail_fast:
                LOGGER(exc_info=NccmpError("verify failed, see above for error info"))
            else:
                LOGGER("verify failed, but fail_fast is False so continuing", level=logging.WARNING)
    if error_ctr > 0:
        LOGGER(exc_info=NccmpError(f"verify failed with {error_ctr=}, see above for error info"))
