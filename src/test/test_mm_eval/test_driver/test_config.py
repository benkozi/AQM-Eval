import tempfile
from pathlib import Path

import yaml
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.context.config import Config, AQMModelConfig, \
    AQMConfig, PackageConfig
from aqm_eval.mm_eval.driver.package.core import PackageKey
from aqm_eval.shared import PathExistingDir


class PackageConfigFactory(ModelFactory[PackageConfig]):

    @classmethod
    def active(cls) -> bool:
        return True


class AQMModelConfigFactory(ModelFactory[AQMModelConfig]):
    _colors = (ii for ii in ("r", "g", "b"))

    @classmethod
    def expt_dir(cls) -> PathExistingDir:
        return Path(tempfile.mkdtemp())

    @classmethod
    def color(cls) -> str:
        return next(cls._colors)

class AQMConfigFactory(ModelFactory[AQMConfig]):

    @classmethod
    def output_dir(cls) -> Path:
        return Path(tempfile.mkdtemp()) / "foo" / "bar"

    @classmethod
    def models(cls):
        return {"eval": AQMModelConfigFactory.build(is_host=True),
                "base1": AQMModelConfigFactory.build(is_host=False),
                "base2": AQMModelConfigFactory.build(is_host=False),}

    @classmethod
    def packages(cls):
        return {ii: PackageConfigFactory.build() for ii in PackageKey}


class ConfigFactory(ModelFactory[Config]):
    __use_defaults__ = True

    @classmethod
    def aqm(cls):
        return AQMConfigFactory.build()

def test(tmp_path: Path, bin_dir: Path) -> None:
    config = ConfigFactory.build()
    out_path = tmp_path / "config.yaml"
    yaml_str = yaml.safe_dump(config.to_yaml(), sort_keys=False)
    print(yaml_str)
    out_path.write_text(yaml_str)
    assert len(config.aqm.models) == 3

    with open(out_path, "r") as f:
        data = yaml.safe_load(f)
    print(data)

    _ = Config.from_yaml(data)
