import tempfile
from pathlib import Path

import pytest
import yaml
from _pytest.fixtures import FixtureRequest
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from polyfactory.factories.pydantic_factory import ModelFactory

from aqm_eval.mm_eval.driver.config import AQMConfig, AQMModelConfig, Config, PackageConfig, PackageKey, PlotKwargs
from aqm_eval.mm_eval.driver.context.srw import SRWContext

_TEST_GLOBALS = {"tmp_path": Path("")}


class PackageConfigFactory(ModelFactory[PackageConfig]):
    @classmethod
    def active(cls) -> bool:
        return True


class PlotKwargsFactory(ModelFactory[PlotKwargs]):
    __use_defaults__ = True


class AQMModelConfigFactory(ModelFactory[AQMModelConfig]):
    __use_defaults__ = True

    @classmethod
    def plot_kwargs(cls) -> PlotKwargs:
        return PlotKwargsFactory.build()


class AQMConfigFactory(ModelFactory[AQMConfig]):
    @classmethod
    def output_dir(cls) -> Path:
        return Path(tempfile.mkdtemp()) / "foo" / "bar"

    @classmethod
    def models(cls) -> dict[str, AQMModelConfig]:
        global _TEST_GLOBALS
        data = {"eval1": {"is_host": True}, "base1": {"is_host": False}, "base2": {"is_host": False}, "base4": {"is_host": False}}
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


@pytest.fixture
def config(tmp_path: Path) -> Config:
    global _TEST_GLOBALS
    _TEST_GLOBALS["tmp_path"] = tmp_path
    return ConfigFactory.build()


@pytest.fixture
def expt_dir(config: Config) -> Path:
    return list(config.aqm.host_model.values())[0].expt_dir


@pytest.fixture(params=["pure", "srw", "srw-no-forecast"])
def config_content(request: FixtureRequest, config: Config, bin_dir: Path) -> dict:
    return get_config_content(bin_dir, config, request.param)


@pytest.fixture()
def config_path_user(expt_dir: Path, bin_dir: Path, config_content: dict) -> Path:
    yaml_content = {
        "metadata": {"description": "config for SRW-AQM, AQM_NA_13km, AEROMMA field campaign"},
        "user": {"RUN_ENVIR": "community", "MACHINE": "GAEAC6", "ACCOUNT": "bil-fire8"},
        "workflow": {
            "USE_CRON_TO_RELAUNCH": True,
            "CRON_RELAUNCH_INTVL_MNTS": 3,
            "EXPT_SUBDIR": "aqm_AQMNA13km_AEROMMA",
            "PREDEF_GRID_NAME": "AQM_NA_13km",
            "CCPP_PHYS_SUITE": "FV3_GFS_v16",
            "DATE_FIRST_CYCL": "2023060112",
            "DATE_LAST_CYCL_MM": "2023060212",
        },
    }
    yaml_content.update(config_content)
    yaml_path = expt_dir / "config.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f)
    return yaml_path


def get_config_content(bin_dir: Path, config: Config, config_src: str) -> dict:
    match config_src:
        case "pure":
            new_content = config.to_yaml()
        case "srw":
            srw_config = bin_dir / "srw-config.yaml"
            srw_config_raw = srw_config.read_text()
            srw_config_raw = srw_config_raw.replace("!int '{{ platform.NCORES_PER_NODE }}'", "100")
            new_content = yaml.safe_load(srw_config_raw)
        case "srw-no-forecast":
            srw_config = bin_dir / "srw-config.yaml"
            srw_config_raw = srw_config.read_text()
            srw_config_raw = srw_config_raw.replace("!int '{{ platform.NCORES_PER_NODE }}'", "100")
            new_content = yaml.safe_load(srw_config_raw)
            new_content["melodies_monet_parm"]["aqm"]["no_forecast"] = True
            new_content["melodies_monet_parm"]["aqm"]["models"]["base1"] = config.aqm.models["base1"].model_dump(mode="json")
        case _:
            raise NotImplementedError(config_src)
    return new_content


@pytest.fixture()
def config_path_rocoto(expt_dir: Path) -> Path:
    yaml_content = {"foo": "bar", "foo2": {"second": "baz"}}
    yaml_path = expt_dir / "rocoto_defns.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f)
    return yaml_path


@pytest.fixture()
def config_path_var_defns(tmp_path: Path, expt_dir: Path, config_content: dict) -> Path:
    path = tmp_path / "NaturalEarth"
    path.mkdir(exist_ok=True, parents=True)
    yaml_content = {"platform": {"FIXshp": f"{str(path)}"}}
    yaml_content.update(config_content)
    yaml_path = expt_dir / "var_defns.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f)
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
    config_path_user: Path,
    config_path_rocoto: Path,
    config_path_var_defns: Path,
    dummy_phy_dyn_files: None,
) -> SRWContext:
    return SRWContext(expt_dir=expt_dir)


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
