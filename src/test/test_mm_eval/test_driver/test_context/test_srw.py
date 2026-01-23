from aqm_eval.mm_eval.driver.context.srw import SRWContext


def test() -> None:
    """Test default model configurations work as expected with default arguments."""
    data = {
        "workflow": {
            "EXPT_BASEDIR": "/tmp/expt_dirs",
            "EXPT_SUBDIR": "aqmv8_sens_vdflev3_met-fch_xkz.1",
            "DATE_LAST_CYCL_MM": "2023081512",
            "DATE_FIRST_CYCL": "2023080112",
        },
        "platform": {"FIXshp": "/tmp"},
        "user": {"MACHINE": "GAEAC6"},
        "melodies_monet_parm": {
            "aqm": {
                "active": True,
                "no_forecast": True,
                "run_mode": "strict",
                "models": {
                    "aqmv8_candev_off_base": {
                        "expt_dir": "/tmp/expt_dirs/aqmv8_candev_off",
                        "plot_kwargs": {"color": "g"},
                    },
                    "aqmv8_candev_vdflev3_met-fch_xkz.1": {
                        "expt_dir": "/tmp/expt_dirs/aqmv8_candev_vdflev3_met-fch_xkz.1",
                        "plot_kwargs": {"color": "r"},
                    },
                },
                "scorecards": {},
                "packages": {
                    "aqs_pm": {
                        "active": False,
                        "observation_template": "/tmp/Observations/AQS/pm25_spec_daily/AQS_20230801_20230901.nc",
                        "execution": {"prep": {"batchargs": {"walltime": "06:00:00"}}},
                    },
                    "aqs_voc": {
                        "active": False,
                        "observation_template": "/tmp/Observations/AQS/vocs/AQS_20230801_20230901.nc",
                    },
                    "chem": {
                        "active": False,
                        "observation_template": "/tmp/Observations/AirNow/AirNow_20230801_20230901.nc",
                        "execution": {"tasks": {"spatial_overlay": {"batchargs": {"nodes": 2, "walltime": "08:00:00"}}}},
                    },
                    "ish": {
                        "active": True,
                        "observation_template": "/tmp/Observations/ISH/ISH-Lite_US_20230801_20230901.nc",
                        "execution": {"prep": {"batchargs": {"walltime": "02:00:00"}}},
                    },
                },
                "task_defaults": {"execution": {"batchargs": {"walltime": "03:00:00"}}},
            }
        },
    }
    _ = SRWContext.model_validate(data)
