# AQM-Eval

Scripts and utilities related to UFS-AQM evaluation and verification.

## Installation

```shell
branch_or_tag=develop
git clone -b ${branch_or_tag} https://github.com/NOAA-EPIC/AQM-Eval
cd AQM-Eval
conda env create -f environment.yml
conda run -n aqm-eval pip install .

# Optionally run tests
conda run -n aqm-eval pytest src/test
```

## _aqm-data-sync_ Utility

A command line utility to synchronize AQM datasets. Currently, tuned to specialized use cases related to Short-Range Weather App use cases. Only S3 download is supported.

### Usage
#tdk:re-generate documentation
```shell
Usage: aqm-data-sync time-varying [OPTIONS]

 Download time varying input data for UFS-AQM.

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --dst-dir                    PATH                 Destination directory  │
│                                                      for sync.              │
│                                                      [default: None]        │
│                                                      [required]             │
│    --first-cycle-date           TEXT                 First cycle date in    │
│                                                      yyyymmddhh format.     │
│                                                      Required if --use-case │
│                                                      is not provided.       │
│                                                      [default: None]        │
│    --fcst-hr                    INTEGER              Forecast hour.         │
│                                                      [default: 0]           │
│    --last-cycle-date            TEXT                 Last cycle date in     │
│                                                      yyyymmddhh format. If  │
│                                                      not provided, defaults │
│                                                      to 24 hours after      │
│                                                      --first-cycle-date.    │
│                                                      [default: None]        │
│    --use-case                   [UNDEFINED|AEROMMA]  Use case.              │
│                                                      [default: UNDEFINED]   │
│    --max-concurrent-req…        INTEGER              Maximum number of      │
│                                                      concurrent requests.   │
│                                                      [default: 5]           │
│    --dry-run                                         Dry run. Nothing will  │
│                                                      be materially          │
│                                                      synchronized.          │
│    --snippet                                         If provided, download  |
|                                                      data for two forecast  |
|                                                      cycles (e.g. two days).|
│    --help                                            Show this message and  │
│                                                      exit.                  │
└─────────────────────────────────────────────────────────────────────────────┘

 Usage: aqm-data-sync srw-fixed [OPTIONS]

 Download SRW fixed data.

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --dst-dir                        PATH     Destination directory for      │
│                                              sync.                          │
│                                              [default: None]                │
│                                              [required]                     │
│    --max-concurrent-requests        INTEGER  Maximum number of concurrent   │
│                                              requests.                      │
│                                              [default: 5]                   │
│    --dry-run                                 Dry run. Nothing will be       │
│                                              materially synchronized.       │
│    --help                                    Show this message and exit.    │
└─────────────────────────────────────────────────────────────────────────────┘

 Usage: aqm-data-sync observations [OPTIONS]

 Download observations for UFS-AQM evaluation.


┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --dst-dir                        PATH     Destination directory for      │
│                                              sync.                          │
│                                              [default: None]                │
│                                              [required]                     │
│    --max-concurrent-requests        INTEGER  Maximum number of concurrent   │
│                                              requests.                      │
│                                              [default: 5]                   │
│    --dry-run                                 Dry run. Nothing will be       │
│                                              materially synchronized.       │
│    --help                                    Show this message and exit.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## _aqm-mm-eval_ Utility

A command line utility wrapping MELODIES MONET configuration files to run a standard set of evaluation and verification tasks for UFS-AQM.

### Usage

```shell
 Usage: aqm-mm-eval yaml-init [OPTIONS]

 Initialize the MELODIES MONET UFS-AQM evaluation from a pure YAML file.

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --yaml-config        PATH  The evaluation's YAML configuration.          │
│                               [default: None]                               │
│                               [required]                                    │
│    --help                     Show this message and exit.                   │
└─────────────────────────────────────────────────────────────────────────────┘

 Usage: aqm-mm-eval yaml-run [OPTIONS]

 Initialize the MELODIES MONET UFS-AQM evaluation from a pure YAML file.

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --yaml-config        PATH  The evaluation's YAML configuration.          │
│                               [default: None]                               │
│                               [required]                                    │
│    --help                     Show this message and exit.                   │
└─────────────────────────────────────────────────────────────────────────────┘

Usage: aqm-mm-eval srw-init [OPTIONS]

 Initialize the MELODIES MONET UFS-AQM evaluation from the SRW workflow.

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --expt-dir        PATH  Experiment directory. [default: None] [required] │
│    --help                  Show this message and exit.                      │
└─────────────────────────────────────────────────────────────────────────────┘

 Usage: aqm-mm-eval srw-run [OPTIONS]

 Run the MELODIES MONET UFS-AQM evaluation from the SRW workflow.

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ *  --expt-dir                PATH                   Experiment directory.   │
│                                                     [default: None]         │
│                                                     [required]              │
│    --package-selector        [chem|met|aqs_pm25|vo  Package selector.       │
│                              cs]                    [default: chem, met,    │
│                                                     aqs_pm25, vocs]         │
│    --task-selector           [save_paired|timeseri  Task selector.          │
│                              es|taylor|spatial_bia  [default: save_paired,  │
│                              s|spatial_overlay|box  timeseries, taylor,     │
│                              plot|multi_boxplot|sc  spatial_bias,           │
│                              orecard_rmse|scorecar  spatial_overlay,        │
│                              d_ioa|scorecard_nmb|s  boxplot, multi_boxplot, │
│                              corecard_nme|csi|stat  scorecard_rmse,         │
│                              s]                     scorecard_ioa,          │
│                                                     scorecard_nmb,          │
│                                                     scorecard_nme, csi,     │
│                                                     stats]                  │
│    --help                                           Show this message and   │
│                                                     exit.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```
