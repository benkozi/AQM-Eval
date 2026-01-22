from aqm_eval.verify.context import VerifyContext
from aqm_eval.verify.runner import run_verify



def test(verify_ctx: VerifyContext) -> None:
    run_verify(verify_ctx)