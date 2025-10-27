from pathlib import Path

import yaml
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.context.config import Config, AQMModelConfig, \
    AQMConfig, PackageConfig


class PackageConfigFactory(ModelFactory[PackageConfig]):
    ...


class AQMModelConfigFactory(ModelFactory[AQMModelConfig]):
    ...


class AQMConfigFactory(ModelFactory[AQMConfig]):

    @classmethod
    def models(cls):
        return tuple(AQMModelConfigFactory.batch(2))

    @classmethod
    def packages(cls):
        return tuple(PackageConfigFactory.batch(2))


class ConfigFactory(ModelFactory[Config]):
    __use_defaults__ = True

    @classmethod
    def aqm(cls):
        return AQMConfigFactory.build()

def test(tmp_path: Path, bin_dir: Path) -> None:
    config = ConfigFactory.build()
    assert len(config.aqm.models) == 2
    out_path = tmp_path / "config.yaml"
    yaml_str = yaml.safe_dump(config.to_yaml_as_json(), sort_keys=False)
    print(yaml_str)
    out_path.write_text(yaml_str)

    with open(out_path, "r") as f:
        data = yaml.safe_load(f)
    print(data)

    loaded = Config.from_yaml_as_json(data)

    #
    # # Or write to a file
    # Path("config.yaml").write_text(yaml_str)