from pathlib import Path

import pytest

from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.driver.context.yaml_eval import YAMLContext


class TestSRWContext:
    def test_init_path_happy(self, srw_context: SRWContext) -> None:
        assert srw_context.date_first_cycle_mm == "2023-06-01-12:00:00"
        assert srw_context.link_simulation == ("2023*",)
        assert srw_context.cartopy_data_dir.exists()

    def test_find_nested_key_happy_second_yaml(self, srw_context: SRWContext) -> None:
        actual = srw_context.find_nested_key(("foo2", "second"))
        assert actual == "baz"

    def test_find_nested_key_sad(self, srw_context: SRWContext) -> None:
        with pytest.raises(KeyError):
            srw_context.find_nested_key(("fail", "badly"))

    def test_find_nested_key_sad_no_child(self, srw_context: SRWContext) -> None:
        with pytest.raises(TypeError):
            srw_context.find_nested_key(("foo", "bar"))


class TestYAMLContext:
    def test_init_happy_path(self, namelist_chem_yaml_config: Path) -> None:
        ctx = YAMLContext(yaml_config=namelist_chem_yaml_config)
        assert isinstance(ctx, YAMLContext)
