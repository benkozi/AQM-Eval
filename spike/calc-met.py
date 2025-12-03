#!/usr/bin/env python
"""
Calculate WS/WD and RH to compare to AirNow
using the extracted phy variables.
"""

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

IN = Path("./in")
OUT = IN

parser = argparse.ArgumentParser(
    description=(
        "Calculate WS/WD and RH from phy file variables to compare to met obs. "
        "Outputs are saved with `_met` added to the input path file name stem. "
        "Input datasets must have: 'ugrd10m', 'vgrd10m', 'spfh2m', 'tmp2m'."
    ),
)

parser.add_argument(
    "PHY",
    help="phy file path(s), possibly pre-processed to select variables etc.",
    nargs="+",
    type=Path,
)

args = parser.parse_args()

ps = args.PHY

for p in ps:
    if not p.is_file():
        raise ValueError(f"path {p.as_posix()!r} doesn't exist or isn't a file.")
    print(p.stem)

    ds = xr.open_dataset(p)

    # Wind speed
    u = ds.ugrd10m
    v = ds.vgrd10m
    assert u.units == v.units == "m/s"
    ws = np.sqrt(u**2 + v**2)
    ws.attrs.update(long_name="10-meter wind speed", units="m/s")

    # Wind direction
    # https://confluence.ecmwf.int/pages/viewpage.action?pageId=133262398
    wd = np.mod(180 + np.rad2deg(np.arctan2(v, u)), 360)
    wd.attrs.update(long_name="10-meter wind direction", units="deg")

    # Calculate RH from specific humidity
    sh = ds.spfh2m  # kg/kg
    t = ds.tmp2m  # K
    t_c = t - 273.15  # deg C
    pres = 1000_00  # Pa; TODO: use ds.pressfc once have
    e_s = 6.1094 * 100 * np.exp(17.625 * t_c / (t_c + 243.04))  # saturation VP; Pa
    w_s = 0.622 * e_s / pres
    rh = 100 * sh / w_s
    assert rh.min() > 0 and rh.quantile(0.9) < 100
    rh = rh.astype(np.float32)
    rh.attrs.update(long_name="2-m relative humidity", units="%")

    # Assign variables
    ds_new = ds.drop_vars(["ugrd10m", "vgrd10m", "spfh2m"]).assign(ws10m=ws, wd10m=wd, rh2m=rh)

    # Save
    p_new = p.with_stem(f"{p.stem}_met")
    print(f"writing: {p_new.as_posix()}")
    ds_new.to_netcdf(p_new)
