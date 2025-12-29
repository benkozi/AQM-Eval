## Download time-varying UFS-SRW inputs
```
aqm-eval data-sync time-varying [OPTIONS]                                             
                                                                                
 Download time varying input data for UFS-AQM.                                  
                                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --dst-dir                    PATH                 Destination directory   │
│                                                      for sync.               │
│                                                      [default: None]         │
│                                                      [required]              │
│    --first-cycle-date           TEXT                 First cycle date in     │
│                                                      yyyymmddhh format.      │
│                                                      Required if --use-case  │
│                                                      is not provided.        │
│                                                      [default: None]         │
│    --fcst-hr                    INTEGER              Forecast hour.          │
│                                                      [default: 0]            │
│    --last-cycle-date            TEXT                 Last cycle date in      │
│                                                      yyyymmddhh format. If   │
│                                                      not provided, defaults  │
│                                                      to 24 hours after       │
│                                                      --first-cycle-date.     │
│                                                      [default: None]         │
│    --use-case                   [UNDEFINED|AEROMMA]  Use case.               │
│                                                      [default: UNDEFINED]    │
│    --max-concurrent-req…        INTEGER              Maximum number of       │
│                                                      concurrent requests.    │
│                                                      [default: 5]            │
│    --dry-run                                         Dry run. Nothing will   │
│                                                      be materially           │
│                                                      synchronized.           │
│    --snippet                                         If provided, download   │
│                                                      data for two forecast   │
│                                                      cycles (e.g. two days). │
│    --help                                            Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Download UFS-SRW fix data
```
aqm-eval data-sync srw-fixed [OPTIONS]                                                
                                                                                
 Download SRW fixed data.                                                       
                                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --dst-dir                        PATH     Destination directory for sync. │
│                                              [default: None]                 │
│                                              [required]                      │
│    --max-concurrent-requests        INTEGER  Maximum number of concurrent    │
│                                              requests.                       │
│                                              [default: 5]                    │
│    --dry-run                                 Dry run. Nothing will be        │
│                                              materially synchronized.        │
│    --help                                    Show this message and exit.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Download MELODIES-MONET observations
```
aqm-eval data-sync observations [OPTIONS]                                             
                                                                                
 Download observations for UFS-AQM evaluation.                                  
                                                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --dst-dir                        PATH     Destination directory for sync. │
│                                              [default: None]                 │
│                                              [required]                      │
│    --max-concurrent-requests        INTEGER  Maximum number of concurrent    │
│                                              requests.                       │
│                                              [default: 5]                    │
│    --dry-run                                 Dry run. Nothing will be        │
│                                              materially synchronized.        │
│    --help                                    Show this message and exit.     │
╰──────────────────────────────────────────────────────────────────────────────╯
```
