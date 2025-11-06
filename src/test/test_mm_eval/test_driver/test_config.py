from pathlib import Path

import yaml

from aqm_eval.mm_eval.driver.config import Config


def test(config: Config, tmp_path: Path) -> None:
    out_path = tmp_path / "config.yaml"
    yaml_str = yaml.safe_dump(config.to_yaml(), sort_keys=False)
    print(yaml_str)
    out_path.write_text(yaml_str)
    assert len(config.aqm.models) == 4

    with open(out_path, "r") as f:
        data = yaml.safe_load(f)
    print(data)
    assert "key" not in data["melodies_monet_parm"]["aqm"]["models"]["eval1"]

    _ = Config.from_yaml(data)


#
# def test_from_yaml_overlay(config: Config) -> None:
#
#     data1 = deepcopy(config.to_yaml())
#     data2 = deepcopy(config.to_yaml())
#     data2["melodies_monet_parm"]["aqm"]["models"]["eval1"]["title"] = "on overridden title"
#
#     actual = Config.from_yaml_overlay(data1, data2)
#     assert actual.aqm.models["eval1"].title == "on overridden title"
