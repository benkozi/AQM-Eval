from pathlib import Path

import pytest
import yaml

from aqm_eval.mm_eval.driver.config import Config, PackageConfig, PackageKey
from test.test_mm_eval.conftest import PackageConfigFactory


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


def test_package_config_allows_none_observation_template() -> None:
    base = PackageConfigFactory.build().model_dump()

    base["observation_template"] = None
    base["active"] = True
    base["key"] = PackageKey.CHEM

    with pytest.raises(ValueError):
        PackageConfig.model_validate(base)

    base["active"] = False
    actual = PackageConfig.model_validate(base)
    assert actual.observation_template is None