"""
ionex_reader
============
A Python package to read, process, and visualise IONEX ionospheric
Total Electron Content (TEC) maps as xarray Datasets.

Public API
----------
read_ionex          Read an IONEX file → xr.Dataset (TEC + RMS maps).
get_grid            Parse lat/lon/height grid from an IONEX header string.
get_epoch           Extract the UTC epoch from a single map block.
get_metadata        Extract version and provenance metadata from the header.
parse_map           Parse a raw TEC map block → numpy array.
parse_rms_map       Parse a raw RMS map block → numpy array.
plot_tec_map        Plot a VTEC map (with optional terminator / geomag lines).
plot_rms_map        Plot a TEC RMS map (with optional overlays).
plot_time_series    Plot TEC or RMS time series at a lat/lon point.

Example
-------
>>> from ionex_reader import read_ionex, plot_tec_map
>>> import matplotlib.pyplot as plt
>>> ds = read_ionex('igsg0010.24i')
>>> fig, ax = plot_tec_map(ds['tec'].isel(time=6), add_terminator=True)
>>> plt.show()
"""

from ionex_reader.ionex import (
    # --- core reader ---
    read_ionex,
    # --- header utilities ---
    get_grid,
    get_epoch,
    get_metadata,
    # --- low-level parsers (useful for custom pipelines) ---
    parse_map,
    parse_rms_map,
    # --- plotting ---
    plot_tec_map,
    plot_rms_map,
    plot_time_series,
)

# Single source of truth — kept in ionex.py, re-exported here so that
# `ionex_reader.__version__` works without importing the submodule directly.
from ionex_reader.ionex import __version__, __author__, __email__

__all__ = [
    # reader
    'read_ionex',
    # header utilities
    'get_grid',
    'get_epoch',
    'get_metadata',
    # parsers
    'parse_map',
    'parse_rms_map',
    # plotting
    'plot_tec_map',
    'plot_rms_map',
    'plot_time_series',
    # package metadata
    '__version__',
    '__author__',
    '__email__',
]
