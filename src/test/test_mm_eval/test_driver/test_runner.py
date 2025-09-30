import pytest
from pydantic import BaseModel

from aqm_eval.logging_aqm_eval import LOGGER
from aqm_eval.mm_eval.driver.context.srw import SRWContext
from aqm_eval.mm_eval.driver.runner import MMEvalRunner


class MMEvalRunnerTestData(BaseModel):
    model_config = {"frozen": True}
    ctx: SRWContext
    expected_n_links: int


@pytest.fixture
def mm_eval_runner_test_data(srw_context: SRWContext, use_base_model: bool) -> MMEvalRunnerTestData:
    if use_base_model:
        expected_n_links = 100
        # expected_fns = { #tdk:rm
        #     "control_multi_boxplot.yaml",
        #     "control_scorecard_nmb.yaml",
        #     "control_timeseries.yaml",
        #     "control_boxplot.yaml",
        #     "namelist.yaml",
        #     "control_stats.yaml",
        #     "control_scorecard_ioa.yaml",
        #     "control_scorecard_nme.yaml",
        #     "control_taylor.yaml",
        #     "control_csi.yaml",
        #     "control_scorecard_rmse.yaml",
        #     "control_save_paired.yaml",
        #     "control_spatial_bias.yaml",
        #     "control_spatial_overlay.yaml",
        # }
    else:
        expected_n_links = 50
        # expected_fns = { #tdk:rm
        #     "control_spatial_bias.yaml",
        #     "control_save_paired.yaml",
        #     "control_stats.yaml",
        #     "control_taylor.yaml",
        #     "control_timeseries.yaml",
        #     "control_csi.yaml",
        #     "control_spatial_overlay.yaml",
        #     "namelist.yaml",
        #     "control_multi_boxplot.yaml",
        #     "control_boxplot.yaml",
        # }
    return MMEvalRunnerTestData(
        expected_n_links=expected_n_links,
        # expected_fns=expected_fns, #tdk:rm
        ctx=srw_context,
    )


class TestMMEvalRunner:
    def test(self, mm_eval_runner_test_data: MMEvalRunnerTestData) -> None:
        """Test "initialize", actually. "run" ensures the failure occurs in xarray when actual data
        is needed."""
        # tdk:test: this should run through all contexts and packages
        ctx = mm_eval_runner_test_data.ctx
        runner = MMEvalRunner(ctx=ctx)

        runner.initialize()

        # Test links for all days are created
        actual_links = [ii for ii in ctx.link_alldays_path.iterdir()]
        assert len(actual_links) == mm_eval_runner_test_data.expected_n_links

        # Test control yaml files are created
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
