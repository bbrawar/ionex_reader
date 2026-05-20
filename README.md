# ionex_reader

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.0-green.svg)](https://github.com/bbrawar/ionex_reader)

A Python package to **read, process, and visualise IONEX ionospheric TEC maps** as [`xarray`](https://docs.xarray.dev/) Datasets.

- Parses TEC and RMS maps from any IONEX-compliant file (JPL, CODE, ESA, CAS, …)  
- Grid coordinates read directly from the file header — never hardcoded  
- Optional overlays: day/night terminator and geomagnetic latitude lines  
- All plots return `(fig, ax)` for downstream customisation  
- `geomag` dependency is **optional** and imported lazily  

---

## Installation

```bash
git clone https://github.com/bbrawar/ionex_reader.git
cd ionex_reader
pip install .
```

To also install the optional `geomag` dependency (needed only for geomagnetic latitude overlays):

```bash
pip install ".[geomag]"
```

---

## Quick Start

```python
from ionex_reader import read_ionex, plot_tec_map, plot_rms_map, plot_time_series
import matplotlib.pyplot as plt

# Read file — fast by default (metadata parsing skipped)
ds = read_ionex('igsg0010.24i')

print(ds)
# Dimensions:  time: 13, latitude: 71, longitude: 73
# Coordinates: time, latitude, longitude
# Variables:   tec, rms

# Plot the TEC map at the 7th epoch
fig, ax = plot_tec_map(ds['tec'].isel(time=6))
plt.show()
```

---

## API Reference

### `read_ionex(filename, read_metadata=False)`

Read an IONEX file and return an `xr.Dataset` containing:

| Variable | Dims | Units | Description |
|----------|------|-------|-------------|
| `tec` | (time, latitude, longitude) | TECU | Vertical Total Electron Content |
| `rms` | (time, latitude, longitude) | TECU | RMS of Vertical TEC |

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filename` | `str` | — | Path to the IONEX file |
| `read_metadata` | `bool` | `False` | Attach `ionex_version` and `run_by` as Dataset attributes |

> Files without RMS maps (common in older IGS products) return an all-NaN `rms` variable with a `UserWarning`.

```python
# Default — fast read, no metadata
ds = read_ionex('igsg0010.24i')

# With metadata attached to ds.attrs
ds = read_ionex('igsg0010.24i', read_metadata=True)
print(ds.attrs)
# {'ionex_version': '1.1', 'run_by': 'JPL', 'ionex_reader_version': '0.3.0'}
```

---

### `get_grid(header)`

Parse the lat/lon/height grid from an IONEX header string.

```python
from ionex_reader import get_grid

with open('igsg0010.24i') as f:
    header = f.read().split('END OF HEADER')[0]

lats, lons, heights = get_grid(header)
print(f'Lat:  {lats[0]}° → {lats[-1]}°   step {abs(lats[1]-lats[0])}°')
print(f'Lon:  {lons[0]}° → {lons[-1]}°   step {abs(lons[1]-lons[0])}°')
print(f'Shell height: {heights[0]} km')
```

---

### `plot_tec_map(tecmap, ...)`

Plot a Vertical TEC map on a global Cartopy projection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tecmap` | `xr.DataArray` or `np.ndarray` | — | 2-D TEC map |
| `add_terminator` | `bool` | `False` | Overlay day/night terminator |
| `terminator_dt` | `datetime` or `None` | `None` | Override epoch for terminator (required for plain numpy arrays) |
| `terminator_kw` | `dict` or `None` | `None` | Styling options for the terminator |
| `add_geomagnetic_lines` | `bool` | `False` | Overlay geomagnetic latitude lines (requires `geomag`) |
| `geomag_kw` | `dict` or `None` | `None` | Styling options for geomagnetic lines |

Returns `(fig, ax)`.

```python
# Basic
fig, ax = plot_tec_map(ds['tec'].isel(time=6))

# With day/night terminator (epoch auto-read from DataArray)
fig, ax = plot_tec_map(ds['tec'].isel(time=6), add_terminator=True)

# Custom terminator styling
fig, ax = plot_tec_map(
    ds['tec'].isel(time=6),
    add_terminator=True,
    terminator_kw=dict(night_alpha=0.35, line_color='yellow', line_width=2),
)

# Terminator only (no night shading)
fig, ax = plot_tec_map(
    ds['tec'].isel(time=6),
    add_terminator=True,
    terminator_kw=dict(show_night_shade=False, line_color='red'),
)

# With geomagnetic latitude lines
fig, ax = plot_tec_map(
    ds['tec'].isel(time=6),
    add_geomagnetic_lines=True,
)

# Custom geomagnetic line styling
fig, ax = plot_tec_map(
    ds['tec'].isel(time=6),
    add_geomagnetic_lines=True,
    geomag_kw=dict(
        step_deg=10,
        highlight_lats=(-30, 0, 30),   # magnetic equator + EIA boundaries
        label_lats=(-60, -30, 0, 30, 60),
        line_color='tomato',
        line_width=0.9,
        highlight_width=2.0,
    ),
)

# All overlays combined
fig, ax = plot_tec_map(
    ds['tec'].isel(time=6),
    add_terminator=True,
    terminator_kw=dict(night_alpha=0.30, line_color='white'),
    add_geomagnetic_lines=True,
    geomag_kw=dict(step_deg=10, line_color='red'),
)

# Plain numpy array — must supply epoch manually
from datetime import datetime
fig, ax = plot_tec_map(
    ds['tec'].isel(time=0).values,
    add_terminator=True,
    terminator_dt=datetime(2024, 1, 1, 12, 0, 0),
)
```

**Terminator keyword options**

| Key | Default | Description |
|-----|---------|-------------|
| `line_color` | `'white'` | Terminator line colour |
| `line_width` | `1.5` | Terminator line width |
| `night_color` | `'navy'` | Night hemisphere fill colour |
| `night_alpha` | `0.25` | Night hemisphere opacity (0–1) |
| `show_night_shade` | `True` | Shade the night hemisphere |

**Geomagnetic line keyword options**

| Key | Default | Description |
|-----|---------|-------------|
| `step_deg` | `10` | Spacing between lines in magnetic degrees |
| `highlight_lats` | `(-30, 0, 30)` | Latitudes drawn thicker / solid |
| `label_lats` | `(-60, -30, 0, 30, 60)` | Latitudes annotated with text labels |
| `line_color` | `'red'` | Colour of all geomagnetic lines |
| `line_alpha` | `0.65` | Opacity of regular lines |
| `line_width` | `0.8` | Width of regular lines |
| `highlight_width` | `1.6` | Width of highlighted lines |

---

### `plot_rms_map(rmsmap, ...)`

Plot a TEC RMS map. Accepts the same `add_terminator`, `terminator_dt`, `terminator_kw`, `add_geomagnetic_lines`, and `geomag_kw` parameters as `plot_tec_map`.

Returns `(fig, ax)`.

```python
fig, ax = plot_rms_map(ds['rms'].isel(time=0))

# With terminator
fig, ax = plot_rms_map(ds['rms'].isel(time=0), add_terminator=True)
```

---

### `plot_time_series(ds, lat, lon, variable='tec')`

Plot the time series of TEC or RMS at the nearest grid point to `(lat, lon)`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `xr.Dataset` | — | Dataset from `read_ionex()` |
| `lat` | `float` | — | Target latitude (°). Snapped to nearest grid point. |
| `lon` | `float` | — | Target longitude (°). Snapped to nearest grid point. |
| `variable` | `str` | `'tec'` | `'tec'` or `'rms'` |

Returns `(fig, ax)`.

```python
# TEC time series at IIT Indore
fig, ax = plot_time_series(ds, lat=22.5, lon=75.5, variable='tec')

# RMS time series
fig, ax = plot_time_series(ds, lat=22.5, lon=75.5, variable='rms')

plt.show()
```

---

### Low-level parsers

Useful when building custom ingestion pipelines.

```python
from ionex_reader import parse_map, parse_rms_map, get_epoch

with open('igsg0010.24i') as f:
    content = f.read()

tec_block = content.split('START OF TEC MAP')[1]   # first map
tec_array = parse_map(tec_block)                    # shape: (n_lat, n_lon)
epoch     = get_epoch(tec_block)                    # datetime object
print(tec_array.shape, epoch)
```

---

## Requirements

| Package | Minimum version | Required |
|---------|----------------|----------|
| `numpy` | 1.21 | ✅ |
| `xarray` | 0.19 | ✅ |
| `matplotlib` | 3.4 | ✅ |
| `cartopy` | 0.20 | ✅ |
| `geomag` | any | Optional (geomagnetic latitude lines only) |

---

## Notes on IONEX files

IONEX files are distributed by IGS analysis centres and can be downloaded from:

- [CDDIS (NASA)](https://cddis.nasa.gov/archive/gnss/products/ionex/)
- [BKG (Germany)](https://igs.bkg.bund.de/root_ftp/IGS/products/ionosphere/)
- [JPL](https://sideshow.jpl.nasa.gov/pub/iono_daily/IONEX_rapid/)

Common file naming: `igsGDDD0.YYi` where `DDD` is the day of year and `YY` is the two-digit year.

---

## Changelog

### v0.3.0
- **Fix** — lat/lon grid parsed from file header (`LAT1/LAT2/DLAT`, `LON1/LON2/DLON`) instead of hardcoded; fixes wrong coordinate axes for non-JPL products
- **Fix** — files with no RMS maps no longer crash; returns NaN-filled array with warning
- **Fix** — `get_metadata` and `get_grid` now scan only the header block, not the whole file
- **Fix** — correct `geomag` import path (`geomag.geomag.GeoMag`, not `geomag.GeoMag`)
- **Fix** — geomagnetic latitude computed from magnetic dip angle; `geo2mag` (non-existent) removed
- **Fix** — geomagnetic grid built once with vectorised loop (~0.7 s); per-point `GeoMag()` instantiation removed
- **Fix** — `plt.rc(dict)` replaced with `plt.rcParams.update()`
- **Fix** — double-backslash in LaTeX ylabel strings corrected
- **Feature** — day/night terminator overlay (pure numpy, no extra dependencies)
- **Feature** — `read_metadata=False` default for faster reads
- **Feature** — all plot functions return `(fig, ax)`
- **Feature** — `get_grid()` exposed as public helper

### v0.2.x
- Intermediate bug fixes (see git log)

### v0.1.0
- Initial release

---

## Contributing

Bug reports and pull requests are welcome at [github.com/bbrawar/ionex_reader](https://github.com/bbrawar/ionex_reader/issues).  
Please attach the IONEX file that triggered the issue where applicable.

---

## Author

**Bhuvnesh Brawar** — IIT Indore, Space Technology & Radio Cosmology Group  
📧 bbrawar@gmail.com

## License

[MIT](LICENSE)

