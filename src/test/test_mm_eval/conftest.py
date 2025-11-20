import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml
from _pytest.fixtures import FixtureRequest
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.config import AQMConfig, AQMModelConfig, Config, PackageConfig, PackageKey, PlatformKey, PlotKwargs
from aqm_eval.mm_eval.driver.context.srw import SRWContext, SrwPlatform, SrwUser, SrwWorkflow

_TEST_GLOBALS: dict[str, Any] = {"tmp_path": None, "bin_dir": None, "host_key": "eval1"}


class PackageConfigFactory(ModelFactory[PackageConfig]):
    @classmethod
    def active(cls) -> bool:
        return True

    @classmethod
    def observation_template(cls) -> str:
        return "a_template*.nc"


class PlotKwargsFactory(ModelFactory[PlotKwargs]):
    __use_defaults__ = True


class AQMModelConfigFactory(ModelFactory[AQMModelConfig]):
    __use_defaults__ = True


class AQMConfigFactory(ModelFactory[AQMConfig]):
    @classmethod
    def output_dir(cls) -> Path:
        return Path(tempfile.mkdtemp()) / "foo" / "bar"

    @classmethod
    def models(cls) -> dict[str, AQMModelConfig]:
        global _TEST_GLOBALS
        data = {
            _TEST_GLOBALS["host_key"]: {"is_host": True, "plot_kwargs": {"color": "g"}},
            "base1": {"is_host": False, "plot_kwargs": {"color": "r"}},
            "base2": {"is_host": False, "plot_kwargs": {"color": "b"}},
            "base4": {"is_host": False, "plot_kwargs": {"color": "w"}},
        }
        ret = {}
        for k, v in data.items():
            expt_dir = _TEST_GLOBALS["tmp_path"] / k
            expt_dir.mkdir(exist_ok=True, parents=True)
            ret[k] = AQMModelConfigFactory.build(**{**data[k], "expt_dir": expt_dir})  # type: ignore[arg-type]
        return ret

    @classmethod
    def packages(cls) -> dict[PackageKey, PackageConfig]:
        return {ii: PackageConfigFactory.build() for ii in PackageKey}


class ConfigFactory(ModelFactory[Config]):
    __use_defaults__ = True
    __use_factory_defaults__ = True

    @classmethod
    def aqm(cls) -> AQMConfig:
        return AQMConfigFactory.build()

    @classmethod
    def start_datetime(cls) -> str:
        return "2023-06-01-12:00:00"

    @classmethod
    def end_datetime(cls) -> str:
        return "2023-06-02-12:00:00"

    @classmethod
    def cartopy_data_dir(cls) -> Path:
        ret = _TEST_GLOBALS["tmp_path"] / "cartopy_data"
        ret.mkdir(exist_ok=True, parents=True)
        return ret

    @classmethod
    def output_dir(cls) -> Path:
        ret = _TEST_GLOBALS["tmp_path"] / "mm_output"
        return ret

    @classmethod
    def run_dir(cls) -> Path:
        ret = _TEST_GLOBALS["tmp_path"] / "mm_run"
        return ret


class SrwWorkflowFactory(ModelFactory[SrwWorkflow]):
    @classmethod
    def EXPT_BASEDIR(cls) -> Path:
        global _TEST_GLOBALS
        return _TEST_GLOBALS["tmp_path"]

    @classmethod
    def EXPT_SUBDIR(cls) -> str:
        global _TEST_GLOBALS
        return _TEST_GLOBALS["host_key"]

    @classmethod
    def DATE_FIRST_CYCL(cls) -> str:
        return "2023060112"

    @classmethod
    def DATE_LAST_CYCL_MM(cls) -> str:
        return "2023060212"


class SrwPlatformFactory(ModelFactory[SrwPlatform]):
    @classmethod
    def FIXshp(cls) -> Path:
        return ConfigFactory.cartopy_data_dir()


class SrwUserFactory(ModelFactory[SrwUser]):
    @classmethod
    def MACHINE(cls) -> str:
        return PlatformKey.GAEAC6.value.upper()


class SRWContextFactory(ModelFactory[SRWContext]):
    __use_defaults__ = True
    __use_factory_defaults__ = True

    @classmethod
    def workflow(cls) -> SrwWorkflow:
        return SrwWorkflowFactory.build()

    @classmethod
    def platform(cls) -> SrwPlatform:
        return SrwPlatformFactory.build()

    @classmethod
    def user(cls) -> SrwUser:
        return SrwUserFactory.build()

    @classmethod
    def melodies_monet_parm(cls) -> dict:
        global _TEST_GLOBALS
        srw_config_path = _TEST_GLOBALS["bin_dir"] / "srw-config.yaml"
        data = yaml.safe_load(srw_config_path.read_text())
        for package_key in PackageKey:
            data["melodies_monet_parm"]["aqm"]["packages"].setdefault(package_key.value, {})["observation_template"] = (
                PackageConfigFactory.build().observation_template
            )
        return data["melodies_monet_parm"]


@pytest.fixture
def config(tmp_path: Path, bin_dir: Path) -> Config:
    global _TEST_GLOBALS
    _TEST_GLOBALS["tmp_path"] = tmp_path
    _TEST_GLOBALS["bin_dir"] = bin_dir
    return ConfigFactory.build()


@pytest.fixture
def expt_dir(config: Config) -> Path:
    return list(config.aqm.host_model.values())[0].expt_dir


@pytest.fixture(params=["pure", "srw", "srw-no-forecast"])
def config_content(request: FixtureRequest, config: Config, bin_dir: Path) -> dict:
    return get_config_content(bin_dir, config, request.param)


# @pytest.fixture()
# def config_path_user(expt_dir: Path, bin_dir: Path, config_content: dict) -> Path:
#     yaml_content = {
#         "metadata": {"description": "config for SRW-AQM, AQM_NA_13km, AEROMMA field campaign"},
#         "user": {"RUN_ENVIR": "community", "MACHINE": "GAEAC6", "ACCOUNT": "bil-fire8"},
#         "workflow": {
#             "USE_CRON_TO_RELAUNCH": True,
#             "CRON_RELAUNCH_INTVL_MNTS": 3,
#             "EXPT_SUBDIR": "aqm_AQMNA13km_AEROMMA",
#             "PREDEF_GRID_NAME": "AQM_NA_13km",
#             "CCPP_PHYS_SUITE": "FV3_GFS_v16",
#             "DATE_FIRST_CYCL": "2023060112",
#             "DATE_LAST_CYCL_MM": "2023060212",
#         },
#     }
#     yaml_content.update(config_content)
#     yaml_path = expt_dir / "config.yaml"
#     with open(yaml_path, "w") as f:
#         yaml.dump(yaml_content, f)
#     return yaml_path


def get_config_content(bin_dir: Path, config: Config, config_src: str) -> dict:
    match config_src:
        case "pure":
            new_content = config.to_yaml()
        case "srw":
            srw_config = bin_dir / "srw-config.yaml"
            srw_config_raw = srw_config.read_text()
            new_content = yaml.safe_load(srw_config_raw)
        case "srw-no-forecast":
            srw_config = bin_dir / "srw-config.yaml"
            srw_config_raw = srw_config.read_text()
            new_content = yaml.safe_load(srw_config_raw)
            new_content["melodies_monet_parm"]["aqm"]["no_forecast"] = True
            models = new_content["melodies_monet_parm"]["aqm"].setdefault("models", {})
            models["base1"] = config.aqm.models["base1"].model_dump(mode="json")
        case _:
            raise NotImplementedError(config_src)
    return new_content


# @pytest.fixture()
# def config_path_rocoto(expt_dir: Path) -> Path:
#     yaml_content = {"foo": "bar", "foo2": {"second": "baz"}}
#     yaml_path = expt_dir / "rocoto_defns.yaml"
#     with open(yaml_path, "w") as f:
#         yaml.dump(yaml_content, f)
#     return yaml_path


@pytest.fixture()
def config_path_var_defns(tmp_path: Path, expt_dir: Path, config_content: dict) -> Path:
    ctx = SRWContextFactory.build()
    data = {"__mm_runtime__": ctx.model_dump(mode="json")}
    yaml_path = expt_dir / "var_defns.yaml"
    yaml_path.write_text(yaml.safe_dump(data))
    # path = tmp_path / "NaturalEarth"
    # path.mkdir(exist_ok=True, parents=True)
    # yaml_content = {"platform": {"FIXshp": f"{str(path)}"}}
    # yaml_content.update(config_content)
    # yaml_path = expt_dir / "var_defns.yaml"
    # with open(yaml_path, "w") as f:
    #     yaml.dump(yaml_content, f)
    return yaml_path


@pytest.fixture()
def dummy_phy_dyn_files(config: Config) -> None:
    for target_model in config.aqm.models.values():
        for dirname in ["2023060112", "2023060212"]:
            out_dir = target_model.expt_dir / dirname
            out_dir.mkdir(exist_ok=False, parents=False)
            for fhr in range(25):
                for prefix in ("phy", "dyn"):
                    new_file = out_dir / f"{prefix}f{fhr:03d}.nc"
                    new_file.touch()


@pytest.fixture
def srw_context(
    expt_dir: Path,
    # config_path_user: Path,
    # config_path_rocoto: Path,
    config_path_var_defns: Path,
    dummy_phy_dyn_files: None,
) -> SRWContext:
    return SRWContext.from_expt_dir(expt_dir)


@pytest.fixture
def namelist_chem_yaml_config(bin_dir: Path, tmp_path: Path) -> Path:
    env = Environment(
        loader=FileSystemLoader(searchpath=bin_dir),
        undefined=StrictUndefined,
    )
    namelist_yaml_config = env.get_template("namelist.chem.yaml.j2").render({"root_path": str(tmp_path)})
    yaml_config = tmp_path / "namelist.chem.yaml"
    with open(yaml_config, "w") as f:
        f.write(namelist_yaml_config)
    (tmp_path / "base_model").mkdir(exist_ok=True, parents=True)
    (tmp_path / "eval_model").mkdir(exist_ok=True, parents=True)
    return yaml_config
