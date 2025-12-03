from pathlib import Path

import pytest
import yaml
from box import Box

from aqm_eval.mm_eval.driver.config import Config, PackageConfig, PackageKey, PlatformKey, TaskKey
from test.test_mm_eval.conftest import PackageConfigFactory


def test(config: Config, tmp_path: Path) -> None:
    out_path = tmp_path / "config.yaml"
    yaml_str = yaml.safe_dump(config.to_yaml(), sort_keys=False)
    print(yaml_str)
    out_path.write_text(yaml_str)
    assert len(config.aqm.models) == 4
    for v in config.aqm.models.values():
        assert v.is_eval_target

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


@pytest.mark.parametrize("platform_key", PlatformKey)
def test_config_from_default_yaml(platform_key: PlatformKey, config: Config) -> None:
    overrides = Box(
        {
            "start_datetime": config.start_datetime,
            "end_datetime": config.end_datetime,
            "cartopy_data_dir": config.cartopy_data_dir,
            "output_dir": config.output_dir,
            "run_dir": config.run_dir,
            "aqm": {"models": {"eval": {"expt_dir": config.aqm.models["eval1"].expt_dir}}},
        },
        default_box=True,
    )

    for package_key in PackageKey:
        overrides["aqm"]["packages"][package_key.value]["observation_template"] = config.aqm.packages[
            package_key
        ].observation_template
        overrides["aqm"]["packages"][package_key.value]["execution"]["tasks"][TaskKey.SPATIAL_OVERLAY]["batchargs"]["nodes"] = 2
    actual = Config.from_default_yaml(platform_key, overrides)
    assert isinstance(actual, Config)
    for package_key in PackageKey:
        batchargs = actual.aqm.packages[package_key].execution.tasks[TaskKey.SPATIAL_OVERLAY].batchargs
        assert batchargs.nodes == 2
        assert batchargs.tasks_per_node == actual.platform_defaults[platform_key].ncores_per_node
    print(yaml.safe_dump(actual.to_yaml(), sort_keys=False))
