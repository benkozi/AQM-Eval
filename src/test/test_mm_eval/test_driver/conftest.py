import tempfile
from pathlib import Path

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.context.config import PackageConfig, AQMModelConfig, AQMConfig, Config
from aqm_eval.mm_eval.driver.package.core import PackageKey

_TEST_GLOBALS = {"tmp_path": Path("")}


class PackageConfigFactory(ModelFactory[PackageConfig]):

    @classmethod
    def active(cls) -> bool:
        return True


class AQMModelConfigFactory(ModelFactory[AQMModelConfig]):
    ...
    # _colors = (ii for ii in ("r", "g", "b"))

    # @classmethod
    # def expt_dir(cls) -> PathExistingDir:
    #     return Path(tempfile.mkdtemp())
    #
    # @classmethod
    # def color(cls) -> str:
    #     return next(cls._colors)


class AQMConfigFactory(ModelFactory[AQMConfig]):

    @classmethod
    def output_dir(cls) -> Path:
        return Path(tempfile.mkdtemp()) / "foo" / "bar"

    @classmethod
    def models(cls):
        global _TEST_GLOBALS
        data = {"eval": {"is_host": True, "color": "r"}, "base1": {"is_host": False, "color": "g"},
                "base2": {"is_host": False, "color": "b"}}
        ret = {}
        for k, v in data.items():
            expt_dir = _TEST_GLOBALS["tmp_path"] / k
            expt_dir.mkdir(exist_ok=True, parents=True)
            ret[k] = AQMModelConfigFactory.build(**{**data[k], "expt_dir": expt_dir})
        return ret

    @classmethod
    def packages(cls):
        return {ii: PackageConfigFactory.build() for ii in PackageKey}


class ConfigFactory(ModelFactory[Config]):
    __use_defaults__ = True

    @classmethod
    def aqm(cls):
        return AQMConfigFactory.build()


@pytest.fixture
def config(tmp_path: Path) -> Config:
    global _TEST_GLOBALS
    _TEST_GLOBALS["tmp_path"] = tmp_path
    return ConfigFactory.build()
