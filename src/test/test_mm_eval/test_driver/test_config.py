import json
from pathlib import Path

import pytest
import yaml
from box import Box
from pydantic_core import ValidationError

from aqm_eval.mm_eval.driver.config import Config, PackageConfig, PackageKey, PlatformKey, TaskKey
from test.test_mm_eval.conftest import PackageConfigFactory


def test(config: Config, tmp_path: Path) -> None:
    out_path = tmp_path / "config.yaml"
    yaml_str = yaml.safe_dump(config.to_yaml(), sort_keys=False)
    print(yaml_str)
    out_path.write_text(yaml_str)
    assert len(config.aqm.models) == 4
    for k, v in config.aqm.models.items():
        assert k == v.key

    with open(out_path, "r") as f:
        data = yaml.safe_load(f)
    print(data)
    assert "key" not in data["melodies_monet_parm"]["aqm"]["models"]["eval1"]

    _ = Config.from_yaml(data)


def test_json_schema() -> None:
    schema = Config.model_json_schema()
    pretty_json = json.dumps(schema, indent=2)
    print(pretty_json)
    # schema_path = Path(aqm_eval.__file__).parent.parent.parent / "docs" / "config.schema.json"
    # schema_path.write_text(pretty_json)


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


def test_aqm_config_validate_model_after_plot_color(config: Config) -> None:
    data = Box(config.model_dump())
    # Assert that there is an error with the same plot color when no forecast is false
    data.aqm.no_forecast = False
    data.aqm.models["eval1"].plot_kwargs.color = "r"
    with pytest.raises(ValidationError):
        _ = Config.model_validate(data)
    # Assert that the host model's plot color is ignored when no forecast is true
    data.aqm.no_forecast = True
    _ = Config.model_validate(data)


def test_aqm_config_validate_model_after_no_shared_model_stems(config: Config) -> None:
    data = Box(config.model_dump())
    data.aqm.models["base"] = data.aqm.models["base1"]
    data.aqm.models["base"].title = "I am unique!"
    data.aqm.models["base"].plot_kwargs.color = "k"
    with pytest.raises(ValidationError) as exc_info:
        _ = Config.model_validate(data)
    assert "Model stems must be unique for wildcard selections" in str(exc_info.value)
