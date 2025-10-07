from pathlib import Path

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.driver.package import AbstractEvalPackage, AQS_VOCEvalPackage, MetEvalPackage, PackageKey
from aqm_eval.mm_eval.driver.runner import MMEvalRunner


class MMEvalRunnerTestData(BaseModel):
    model_config = {"frozen": True}
    ctx: SRWContext
    expected_n_links: int
    expected_ncap2_calls: int
    expected_ncks_calls: int


@pytest.fixture
def mm_eval_runner_test_data(srw_context: SRWContext, use_base_model: bool) -> MMEvalRunnerTestData:
    expected_n_links = (
        (25 * 2) + 48 + 48
    )  # (25 dynf hourly files * 2 cycle directories) + 96 ISH converted files + 96 AQS PM converted files
    expected_ncks_calls = 2 * 24 * 2  # (2 cycle directories * 24 hours * 2 ncks calls)
    expected_ncap2_calls = (15 * 24 * 2) + (
        23 * 24 * 2
    )  # (15 ncap2 ISH calls * 24 hours * 2 cycle directories) + (23 ncap2 AQS PM calls * 24 hours * 2 cycle directories)
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


class TestMMEvalRunner:
    def test(self, mm_eval_runner_test_data: MMEvalRunnerTestData, mocker: MockerFixture) -> None:
        """Test "initialize", actually. "run" ensures the failure occurs in xarray when actual data
        is needed."""

        ctx = mm_eval_runner_test_data.ctx
        runner = MMEvalRunner(ctx=ctx)

        # Test that each package's initialization routine is called.
        m_package_init = mocker.spy(AbstractEvalPackage, "initialize")
        spy_ish_init = mocker.spy(MetEvalPackage, "initialize")
        spy_aqm_voc_init = mocker.spy(AQS_VOCEvalPackage, "initialize")
        _ = mocker.patch.object(AbstractEvalPackage, "_run_ncap2_cmd_", fake_run_ncap2_cmd)
        spy_run_ncap2_cmd = mocker.spy(AbstractEvalPackage, "_run_ncap2_cmd_")
        _ = mocker.patch.object(AbstractEvalPackage, "_run_ncks_cmd_", fake_run_ncks_cmd)
        spy_run_ncks_cmd = mocker.spy(AbstractEvalPackage, "_run_ncks_cmd_")

        runner.initialize()

        assert m_package_init.call_count == len(list(PackageKey)) - 2  # Two overridden initialize methods
        assert spy_ish_init.call_count == 1
        assert spy_aqm_voc_init.call_count == 1
        assert spy_run_ncap2_cmd.call_count == mm_eval_runner_test_data.expected_ncap2_calls
        assert spy_run_ncks_cmd.call_count == mm_eval_runner_test_data.expected_ncks_calls

        # Test links for all days are created
        actual_links = [ii for ii in ctx.link_alldays_path.iterdir()]
        assert len(actual_links) == mm_eval_runner_test_data.expected_n_links

        # Test control yaml files are created
        assert [ii.key for ii in mm_eval_runner_test_data.ctx.mm_packages] == list(PackageKey)
        for package in mm_eval_runner_test_data.ctx.mm_packages:
            LOGGER(f"{package.key=}")
            package_run_dir = ctx.mm_run_dir / package.key.value
            actual_files = package_run_dir.rglob("*")
            expected_filenames = package.task_control_filenames
            expected_filenames.update({"namelist.yaml"})
            assert set([ii.name for ii in actual_files]) == expected_filenames

            with pytest.raises(ValueError) as excinfo:
                runner.run()
            assert str(excinfo.value).startswith("did not find a match in any of xarray's currently installed IO backends")
