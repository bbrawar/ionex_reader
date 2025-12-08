import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime, timedelta
import xarray as xr
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs
import geomag

"""
IONEX Reader & Visualization Toolkit
Author: B. Brawar
Improved Version: Robust IONEX parsing + plotting + time series
"""

# ============================================================
# -------------------- CORE READER ---------------------------
# ============================================================

def read_ionex(filename):
    """
    Read an IONEX file and return an xarray Dataset.
    """
    with open(filename, "r", errors="ignore") as f:
        content = f.read()

    tec_blocks = content.split("START OF TEC MAP")[1:]
    rms_blocks = content.split("START OF RMS MAP")[1:]

    tecmaps = [parse_map(block) for block in tec_blocks]
    rmsmaps = [parse_rms_map(block) for block in rms_blocks]
    epochs  = [get_epoch(block) for block in tec_blocks]

    lat, lon = extract_grid(content)
    metadata = get_metadata(content)

    return create_xarray(tecmaps, rmsmaps, epochs, lat, lon, metadata)


# ============================================================
# -------------------- MAP PARSERS ---------------------------
# ============================================================

def parse_map(block, exponent=-1):
    block = block.split("END OF TEC MAP")[0]
    data_lines = re.split(".*LAT/LON1/LON2/DLON/H\n", block)[1:]
    return np.stack([np.fromstring(l, sep=" ") for l in data_lines]) * 10 ** exponent


def parse_rms_map(block, exponent=-1):
    block = block.split("END OF RMS MAP")[0]
    data_lines = re.split(".*LAT/LON1/LON2/DLON/H\n", block)[1:]
    return np.stack([np.fromstring(l, sep=" ") for l in data_lines]) * 10 ** exponent


# ============================================================
# -------------------- EPOCH HANDLER -------------------------
# ============================================================

def get_epoch(tecmap):
    """
    Extract epoch and handle 24:00:00 rollover.
    """
    epoch_line = tecmap.split("EPOCH OF CURRENT MAP")[0]
    epoch_vals = np.array(epoch_line.split(), dtype=int)
    year, month, day, hour, minute, second = epoch_vals

    if hour == 24:
        return datetime(year, month, day, 0, minute, second) + timedelta(days=1)
    return datetime(year, month, day, hour, minute, second)


# ============================================================
# -------------------- GRID EXTRACTION -----------------------
# ============================================================

def extract_grid(content):
    """
    Extract latitude and longitude grids from IONEX header.
    """
    lat_info = re.search(r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+LAT1 / LAT2 / DLAT", content)
    lon_info = re.search(r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+LON1 / LON2 / DLON", content)

    lat1, lat2, dlat = map(float, lat_info.groups())
    lon1, lon2, dlon = map(float, lon_info.groups())

    latitudes  = np.arange(lat1, lat2 + dlat, dlat)
    longitudes = np.arange(lon1, lon2 + dlon, dlon)

    return latitudes, longitudes


# ============================================================
# -------------------- METADATA ------------------------------
# ============================================================

def get_metadata(content):
    metadata = {}

    v = re.search(r"(\d+\.\d+)\s+IONOSPHERE MAPS\s+GNSS\s+IONEX VERSION / TYPE", content)
    if v:
        metadata["ionex_version"] = v.group(1)

    pgm = re.search(r"(.+?)\s+(.+?)\s+(\d{2}-[A-Z]{3}-\d{2}.*)PGM / RUN BY / DATE", content)
    if pgm:
        metadata["run_by"] = pgm.group(2).strip()
        metadata["creation_date"] = pgm.group(3).strip()

    return metadata


# ============================================================
# -------------------- XARRAY CREATION -----------------------
# ============================================================

def create_xarray(tecmaps, rmsmaps, epochs, lat, lon, metadata):
    ds = xr.Dataset(
        {
            "tec": (["time", "latitude", "longitude"], np.stack(tecmaps)),
            "rms": (["time", "latitude", "longitude"], np.stack(rmsmaps))
        },
        coords={
            "time": epochs,
            "latitude": lat,
            "longitude": lon
        },
        attrs=metadata
    )
    return ds


# ============================================================
# -------------------- GEOMAG LINES --------------------------
# ============================================================

def plot_geomagnetic_latitude_lines(ax):
    gm = geomag.GeoMag()
    lons = np.arange(-180, 181, 2)

    for lat in np.arange(-60, 61, 10):
        mag_lat = [gm.geo2mag(lat, lon)[0] for lon in lons]
        ax.plot(lons, mag_lat, "r--", linewidth=0.8, transform=ccrs.PlateCarree())


# ============================================================
# -------------------- MAP PLOTTING --------------------------
# ============================================================

def plot_tec_map(tecmap, time=None, add_geomagnetic_lines=False):
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(10, 5), subplot_kw={"projection": proj})

    ax.coastlines()
    h = ax.imshow(
        tecmap, cmap="viridis", vmin=0, vmax=100,
        extent=[-180, 180, -90, 90], transform=proj
    )

    if add_geomagnetic_lines:
        plot_geomagnetic_latitude_lines(ax)

    gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.4)
    gl.top_labels = False
    gl.right_labels = False

    title = f"VTEC Map {time}" if time else "VTEC Map"
    ax.set_title(title)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)
    cb = plt.colorbar(h, cax=cax)
    cb.set_label("TECU")

    plt.show()


def plot_rms_map(rmsmap, time=None):
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(10, 5), subplot_kw={"projection": proj})

    ax.coastlines()
    h = ax.imshow(
        rmsmap, cmap="plasma", vmin=0, vmax=10,
        extent=[-180, 180, -90, 90], transform=proj
    )

    gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.4)
    gl.top_labels = False
    gl.right_labels = False

    title = f"RMS Map {time}" if time else "RMS Map"
    ax.set_title(title)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.1)
    cb = plt.colorbar(h, cax=cax)
    cb.set_label("TECU")

    plt.show()


# ============================================================
# -------------------- TIME SERIES ---------------------------
# ============================================================

def plot_time_series(ds, lat, lon, variable="tec"):
    da = ds[variable].sel(latitude=lat, longitude=lon, method="nearest")

    plt.figure(figsize=(10, 5))
    plt.plot(ds.time, da)
    plt.xlabel("Time (UTC)")
    plt.ylabel("TECU")
    plt.title(f"{variable.upper()} at ({lat:.1f}°, {lon:.1f}°)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
