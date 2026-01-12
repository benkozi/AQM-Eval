import base64
import json

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.rocoto.srw_model import AqmTaskGroup


def cli_arg_to_json(arg: str) -> dict:
    json_bytes = base64.urlsafe_b64decode(arg.encode("ascii"))
    return json.loads(json_bytes.decode("utf-8"))


def json_to_cli_arg(data: dict) -> str:
    json_bytes = json.dumps(data).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("ascii")


def srw_data_to_json(srw_data: str) -> None:
    data_from_srw = cli_arg_to_json(srw_data)
    LOGGER(f"{data_from_srw=}")
    ctx = SRWContext.model_validate(data_from_srw)
    tg = AqmTaskGroup.from_config(ctx.mm_config)
    tg_yaml = tg.to_yaml()
    # LOGGER(f"{tg_yaml=}")
    print(json_to_cli_arg(tg_yaml))
