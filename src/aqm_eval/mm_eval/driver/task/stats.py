from aqm_eval.base import AeBaseModel


class StatsTask(AeBaseModel):
    stat_list: list[str]
    round_output: int
    output_table: bool
    output_table_kwargs: dict
    domain_type: list[str]
    domain_name: list[str]
    data: list[str]
