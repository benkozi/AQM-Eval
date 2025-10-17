from functools import cached_property
from pathlib import Path
from unittest.mock import Mock

import melodies_monet  # type: ignore[import-untyped]
import numpy as np
import pytest
import xarray as xr
from pydantic import BaseModel
from pytest_mock import MockerFixture

from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.driver.package import (
    AbstractEvalPackage,
    PackageKey,
    TaskKey,
    package_key_to_class, PM_PrepContext, run_pm_preprocess_computation,
)
from aqm_eval.shared import PathExisting, ncdump


class MMEvalRunnerTestData(BaseModel):
    model_config = {"frozen": True}
    ctx: SRWContext
    package_class: type[AbstractEvalPackage]
    expected_n_links: int
    expected_ncap2_calls: int
    expected_ncks_calls: int


@pytest.fixture(params=tuple(PackageKey))
def package_key(request: pytest.FixtureRequest) -> PackageKey:
    return request.param


@pytest.fixture
def mm_eval_runner_test_data(srw_context: SRWContext, use_base_model: bool, package_key: PackageKey) -> MMEvalRunnerTestData:
    package_class = package_key_to_class(package_key)
    expected_n_links = 25 * 2  # 25 dynf hourly files * 2 cycle directories
    expected_ncap2_calls = 0
    expected_ncks_calls = 0

    match package_key:
        case PackageKey.ISH:
            expected_n_links = 24 * 2  # 24 dynf hourly files * 2 cycle directories
            expected_ncap2_calls = 15 * 24 * 2  # 15 ncap2 calls * 24 hours * 2 cycle directories
        case PackageKey.AQS_PM:
            expected_n_links = 24 * 2  # 24 dynf hourly files * 2 cycle directories
            expected_ncap2_calls = 23 * 24 * 2  # 15 ncap2 calls * 24 hours * 2 cycle directories
            expected_ncks_calls = 2 * 24 * 2  # 2 ncks calls * 24 hours * 2 cycle directories

    if use_base_model:
        # Two model adjustment
        expected_n_links *= 2
        expected_ncks_calls *= 2
        expected_ncap2_calls *= 2

    return MMEvalRunnerTestData(
        expected_n_links=expected_n_links,
        expected_ncap2_calls=expected_ncap2_calls,
        ctx=srw_context,
        expected_ncks_calls=expected_ncks_calls,
        package_class=package_class,
    )


def fake_run_ncap2_cmd(self: AbstractEvalPackage, cmd: list[str]) -> None:
    out_file = Path(cmd[-1])
    if "-A" not in cmd:
        out_file.touch()
    else:
        assert out_file.exists()


def fake_run_ncks_cmd(self: AbstractEvalPackage, cmd: list[str]) -> None:
    out_file = Path(cmd[-1])
    if "-A" not in cmd:
        out_file.touch()
    else:
        assert out_file.exists()


def test_all_packages(mm_eval_runner_test_data: MMEvalRunnerTestData, mocker: MockerFixture) -> None:
    package = mm_eval_runner_test_data.package_class.model_validate(dict(ctx=mm_eval_runner_test_data.ctx))

    # Test initialize --------------------------------------------------------------------------

    _ = mocker.patch.object(AbstractEvalPackage, "_run_ncap2_cmd_", fake_run_ncap2_cmd)
    spy_run_ncap2_cmd = mocker.spy(AbstractEvalPackage, "_run_ncap2_cmd_")
    _ = mocker.patch.object(AbstractEvalPackage, "_run_ncks_cmd_", fake_run_ncks_cmd)
    spy_run_ncks_cmd = mocker.spy(AbstractEvalPackage, "_run_ncks_cmd_")

    package.initialize()

    assert spy_run_ncap2_cmd.call_count == mm_eval_runner_test_data.expected_ncap2_calls
    assert spy_run_ncks_cmd.call_count == mm_eval_runner_test_data.expected_ncks_calls

    actual_data = [ii.name for ii in package.link_alldays_path.iterdir()]
    assert len(actual_data) == mm_eval_runner_test_data.expected_n_links

    actual_files = package.run_dir.rglob("*.yaml")
    expected_filenames = package.task_control_filenames
    expected_filenames.update({"namelist.yaml"})
    assert set([ii.name for ii in actual_files]) == expected_filenames

    assert package.link_alldays_path.name in [ii.name for ii in package.run_dir.iterdir()]

    # Test run ---------------------------------------------------------------------------------

    m_analysis = Mock()
    m_analysis.read_control = Mock()
    m_analysis.open_models = Mock()
    m_analysis.open_obs = Mock()
    m_analysis.pair_data = Mock()
    m_analysis.save_analysis = Mock()
    _ = mocker.patch.object(melodies_monet.driver, "analysis", return_value=m_analysis)

    package.run(TaskKey.SAVE_PAIRED)

    assert package.mm_package_output_dir.exists()

    m_analysis.read_control.assert_called_once()
    m_analysis.open_models.assert_called_once()
    m_analysis.open_obs.assert_called_once()
    m_analysis.pair_data.assert_called_once()
    m_analysis.save_analysis.assert_called_once()


class ContextForTest(BaseModel):
    model_config = {"frozen": True}

    root_dir: PathExisting

    t_shp: int = 10
    y_shp: int = 20
    x_shp: int = 10

    derived_varnames: tuple[str, ...] = ("air_density", "pm25_so4", "pm25_no3", "pm25_nh4", "pm25_ec", "poci", "pocj", "poc", "soc", "soci", "socj", "pm25_oc")

    # @computed_field
    # @cached_property
    # def chunk(self) -> int:
    #     return int(self.x_shp / 2)

    # @cached_property
    # def field_array(self) -> xr.DataArray:
    #     shape = (self.y_shp, self.x_shp)
    #     data = np.random.random(shape)
    #     return xr.DataArray(data, dims=("y", "x"))

    @cached_property
    def pm_prep_ctx(self) -> PM_PrepContext:
        dyn_path = self.root_dir / "dyn.nc"
        self.dataset_dyn.to_netcdf(dyn_path)

        phy_path = self.root_dir / "phy.nc"
        self.dataset_phy.to_netcdf(phy_path)

        return PM_PrepContext(out_path=self.root_dir / "out.nc",
                              dyn_path=dyn_path,
                              phy_path=phy_path,
                              dask_num_workers=2, )

    @cached_property
    def dataset_dyn(self) -> xr.Dataset:
        return xr.Dataset({ii: self.create_data_array(ii) for ii in PM_PrepContext.model_fields["dyn_varnames"].default})

    @cached_property
    def dataset_phy(self) -> xr.Dataset:
        return xr.Dataset({ii: self.create_data_array(ii) for ii in PM_PrepContext.model_fields["phy_varnames"].default})

    def create_data_array(self, name: str) -> xr.DataArray:
        shape = (self.t_shp, self.y_shp, self.x_shp)
        data = np.random.random(shape)
        return xr.DataArray(data, name=name, dims=("time", "y", "x"))


def test_run_pm_preprocess_computation(tmp_path: Path) -> None:
    # kwds = dict(out_path = tmp_path / "out.nc",
    # dyn_path = tmp_path / "dyn.nc",
    # phy_path = tmp_path / "phy.nc",
    #             chunks={"y": 500, "x": 500})
    # pm_prep_ctx = PM_PrepContext.model_validate(kwds)
    np.random.seed(0)

    test_ctx = ContextForTest(root_dir=tmp_path)

    # dask.config.set(scheduler="processes", num_workers=2)
    # dask.config.set(scheduler="threads", num_workers=test_ctx.pm_prep_ctx.dask_num_workers)
    # LOGGER(f"{dask.config.get('scheduler', default='not set')=}")
    # LOGGER(f"{dask.config.get('num_workers', default='not set')=}")
    # LOGGER(f"{dask.config.get('num_threads', default='not set')=}")

    # result = pm_prep(test_ctx.pm_prep_ctx).compute()

    result = run_pm_preprocess_computation(test_ctx.pm_prep_ctx)

    assert result.dims == {'time': 1, 'y': test_ctx.y_shp, 'x': test_ctx.x_shp}
    assert set(result.data_vars) == set(test_ctx.pm_prep_ctx.dyn_varnames + test_ctx.pm_prep_ctx.phy_varnames + test_ctx.derived_varnames)
    # print(result)
    result.to_netcdf(test_ctx.pm_prep_ctx.out_path)

def test_run_pm_preprocess_computation_gc6(tmp_path: Path) -> None:

    for fhr in range(25):
        fhr_str = f"{fhr:02d}"
        dyn_path = Path(f"/gpfs/f6/bil-fire8/scratch/Benjamin.Koziol/sandbox/srw/benkozi/mm-pkgs2/expt_dirs/aqm_AQMNA13km_AEROMMA_success/2023060112/dynf0{fhr_str}.nc")
        if fhr == 0:
            ncdump(dyn_path)
        pm_prep_ctx = PM_PrepContext(out_path=Path("/autofs/ncrc-svm1_home2/Benjamin.Koziol/htmp") / f"out{fhr_str}.nc",
                              dyn_path=dyn_path,
                              phy_path=Path(f"/gpfs/f6/bil-fire8/scratch/Benjamin.Koziol/sandbox/srw/benkozi/mm-pkgs2/expt_dirs/aqm_AQMNA13km_AEROMMA_success/2023060112/phyf0{fhr_str}"),
                              dask_num_workers=100,
                                     chunks={"grid_xt": 100, "grid_yt": 100})

        result = run_pm_preprocess_computation(pm_prep_ctx)
        result.to_netcdf(pm_prep_ctx.out_path)
        if fhr == 0:
            ncdump(pm_prep_ctx.out_path)
