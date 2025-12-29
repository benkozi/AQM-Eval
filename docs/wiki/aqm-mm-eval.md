# Install & Run

It is recommended to quickly read through the full wiki content before running an evaluation.

## Install AQM-Eval

### Standalone Installation

```shell
branch="main"
git clone -b ${branch} https://github.com/NOAA-EPIC/AQM-Eval.git
cd AQM-Eval
conda env create -f environment.yml  # Optionally use environment-dev.yml if installing a development environment
pip install .  # Optionally use "pip -e" to install in editable mode
conda run -n aqm-eval aqm-mm-eval --help
```

### Installation in the UFS-SRW Environment

#### Clone and build the UFS-SRW

Follow the UFS-SRW [clone and build instructions](https://ufs-srweather-app.readthedocs.io/en/develop/UsersGuide/BuildingRunningTesting/Quickstart.html#building-and-running-the-ufs-srw-application). The full SRW build is needed when running a forecast, and the `srw_app` conda environment is also needed. It's easiest to install the conda environment via the build script.

#### Clone the AQM-Eval repository

Clone `AQM-Eval` in a directory external to the SRW repository.

```shell
branch="main"
git clone -b ${branch} https://github.com/benkozi/AQM-Eval.git
```

#### Install the AQM-Eval conda environment

1. Activate the `srw-app` conda environment following [these instructions](https://ufs-srweather-app.readthedocs.io/en/develop/UsersGuide/BuildingRunningTesting/Quickstart.html#building-and-running-the-ufs-srw-application).
2. Install the AQM-Eval conda environment:
```shell
cd <AQM-Eval clone directory>
conda env create -f environment.yml
conda run -n aqm-eval pip install .
```

## Run the Evaluation

1. Copy the UFS-SRW experiment configuration to `config.yaml` like normal.
2. Update the configuration following examples from [UFS-SRW Cookbooks](https://github.com/NOAA-EPIC/AQM-Eval/wiki/aqm%E2%80%90mm%E2%80%90eval#ufs-srw-cookbooks).
3. Generate and launch the workflow.
4. When the MM tasks execute, "run" data composed of configuration files and linked/pre-processed data will appear in the `mm_run` directory. Outputs comprising plots, statistics, and paired files appear in `mm_output` unless otherwise configured.

# Configuration

The wrapper uses a single configuration file to drive task creation and the runtime environment. Currently, the wrapper is tuned to work with the [UFS-SRW](https://github.com/ufs-community/ufs-srweather-app) workflow engine ([uwtools](https://uwtools.readthedocs.io/en/main/) generating a [rocoto](https://christopherwharrop.github.io/rocoto/) workflow). For example configurations to use with the UFS-SRW see the [UFS-SRW Cookbooks](#ufs-srw-cookbooks) section below. This section will describe the configuration format with background information on key terminology. 

* Main configuration file template: [config-default.yaml](https://github.com/benkozi/AQM-Eval/blob/feat/additional-mm-pkgs-dev/src/aqm_eval/mm_eval/yaml_template/config-default.yaml)
* A JSON schema mapping to the YAML: [config.schema.json](https://github.com/benkozi/AQM-Eval/blob/feat/additional-mm-pkgs-dev/docs/config.schema.json)
  * Searching the JSON schema can provide descriptions for the configuration elements.

## Evaluation Packages

An "evaluation package" is a collection of MM plots (and associated statistics) tied to a specific observation dataset (i.e., AirNow). Packages have an initialization behavior which will find and link necessary model and observation data. In some cases, packages may need to pre-process model data to convert units or create derived variables. Packages have a dedicated key defined by a `PackageKey`.

## Evaluation Tasks

An "evaluation task" maps directly to an MM output -- a paired dataset, plot, or statistics file. Tasks have a dedicated `TaskKey` to uniquely identify them. The exception is a scorecard, which will have a suffix associated with a `ScorecardMethod` such as `rmse`. Note, that the task terminology should not be confused with a `rocoto` task which defines a single HPC job.

## Forecast Modes

The wrapper can run in two modes determined by the boolean `melodies_monet_parm.aqm.no_forecast` flag.
* `true`: In this mode, the UFS-SRW forecast and associated task groups _will not_ execute. The evaluation will use the host experiment directory as a "template" directory and look for external experiment directories to use as evaluation targets. It is expected that all experiments have equivalent cycling characteristics such that model outputs align and diagnostic and physics output can be found across all models/experiments.
* `false`: In this mode, the host experiment will be part of the evaluation. The option to evaluate other experiments remains. The cycling similarities requirement still applies. The key characteristic of this mode is that the evaluation will run following the UFS-SRW forecast task.

## Observational Datasets

Observation dataset templates are configured per-package via the `melodies_monet_parm.aqm.packages.<PackageKey>.observation_template` key. The observation dataset must cover the entire simulation window. Observation data is expected in MM format.

## Multi-Model Configuration

Multiple models may be configured in the same evaluation. There is no upper limit to the number of models, but it is worth noting that increasing the number of models will increase the runtime of the evaluation.

At least one model configuration must have `is_host: true`. See the [Forecast Modes](#forecast-modes) section for additional information on host models. In general, the UFS-SRW setup will automatically configure the host model.

### Scorecards

Any number of scorecard combinations may be configured. A scorecard must have a unique identifier key and a mapping containing the control and sensitivity model labels. For example:
```yaml
...
scorecards:
  ScoreCard-AB:
    control: model-a
    sensitivity: model-b
  Scorecard-CD:
    control: model-c
    sensitivity: model-d
...
```

## Batch Execution Arguments

Batch execution arguments are configured at the package and task levels. There are also platform and task defaults. Currently, platform defaults are only used to define the number of cores per node on a given platform.

* `melodies_monet_parm.aqm.packages.<PackageKey>.execution.prep`: Package-specific execution arguments for the prep/initialization tasks. 
* `melodies_monet_parm.aqm.packages.<PackageKey>.execution.tasks`: Task-specific execution arguments. Use the tasks's unique key to identify which task to override defaults.
* `melodies_monet_parm.aqm.task_defaults`: Default task execution arguments to use without overrides.
* `melodies_monet_parm.platform_defaults`: Platform-specific execution arguments.

# UFS-SRW Cookbooks

This section contains some cookbooks that can be adapted to run MM-enabled evaluations in the UFS-SRW.

## Limitations (Gotchas)

* Evaluation expects output at a _24 hour_ cycling frequency. This frequency constraint can eventually be relaxed. So, right now, `INCR_CYCL_FREQ: 24` is required.
* Out-of-the-box execution batch arguments will likely need to be adjusted for your use case.

## Evaluation with a Forecast - Single Model

As simple as it gets for running a single model evaluation.

```yaml
...
workflow:
  ...
  DATE_LAST_CYCL_MM: <last UFS-SRW cycle date for the evaluation>
  ...
  taskgroups:
    - parm/wflow/prep.yaml
    - parm/wflow/aqm_prep.yaml
    - parm/wflow/coldstart.yaml
    - parm/wflow/post.yaml
    - parm/wflow/aqm_post_melodies_monet.yaml
...

melodies_monet_parm:
  aqm:
    active: true  # The evaluation will be enabled.
    no_forecast: false  # Forecast task(s) will run before the evaluation. The "host" model will be an evaluation target.
    models:  # Models to evaluation. Only one target model in this scenario.
      eval:  # Unique model key/label.
        title: "Evaluation Target"  # Unique model title used for plotting. 
        plot_kwargs:  # Plotting overrides (only color is required as it needs to be unique).
          color: g
    packages:
      aqs_pm:
        active: true  # Packages can be disabled by setting this value to false.
        # An observation file template is required for each package.
        observation_template: /data/aqm-use-case-download/Observations/AQS/pm25_spec_daily/AQS_20230601_20230701.nc
      aqs_voc:
        active: true
        observation_template: /data/aqm-use-case-download/Observations/AQS/vocs/AQS_20230601_20230701.nc
      chem:
        active: true
        observation_template: /data/aqm-use-case-download/Observations/AirNow/AirNow_20230601_20230701.nc
      ish:
        active: true
        observation_template: /data/aqm-use-case-download/Observations/ISH/ISH-Lite_20230601_20230701.nc
```

## Evaluation using Three External Experiments with Scorecards

Note: There is a `rocoto` hack involved with the `no_forecast` experiment configuration. When `no_forecast: true`, the UFS-SRW variable `DATE_LAST_CYCL` should be set 48 hours after `DATE_FIRST_CYCL`. This setting allows `rocoto` to cycle appropriately. The MM evaluation executes in the second 24-hour "cycle".

```yaml
...
workflow:
  ...
  DATE_LAST_CYCL: <48 hours after DATE_FIRST_CYCL>
  DATE_LAST_CYCL_MM: <last UFS-SRW cycle date for the evaluation>
  ...
  taskgroups:
    - parm/wflow/aqm_post_melodies_monet.yaml
...

melodies_monet_parm:
  aqm:
    active: true  # The evaluation will be enabled.
    no_forecast: true  # Forecast task will not run. Current experiment directory used for data and workflow orchestration only.
    models:  # Models to evaluate
      target-a:
        title: "Target A" 
        expt_dir: /path/to/experiment/directory/a
        plot_kwargs:
          color: g
      target-b:
        title: "Target B" 
        expt_dir: /path/to/experiment/directory/b
        plot_kwargs:
          color: k
      target-c:
        title: "Target C" 
        expt_dir: /path/to/experiment/directory/c
        plot_kwargs:
          color: r
    # Each scorecard requires a unique identifier key and a control/sensitivity mapping to model keys (labels).
    scorecards:
      Scorecard-AB:
        control: target-a
        sensitivity: target-b
      Scorecard-BC:
        control: target-b
        sensitivity: target-c
      Scorecard-AC:
        control: target-a
        sensitivity: target-c
    packages:
      aqs_pm:
        active: true  # Packages can be disabled by setting this value to false.
        # An observation file template is required for each package.
        observation_template: /data/aqm-use-case-download/Observations/AQS/pm25_spec_daily/AQS_20230601_20230701.nc
      aqs_voc:
        active: true
        observation_template: /data/aqm-use-case-download/Observations/AQS/vocs/AQS_20230601_20230701.nc
      chem:
        active: true
        observation_template: /data/aqm-use-case-download/Observations/AirNow/AirNow_20230601_20230701.nc
      ish:
        active: true
        observation_template: /data/aqm-use-case-download/Observations/ISH/ISH-Lite_20230601_20230701.nc
```