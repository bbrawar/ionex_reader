"""
ionex.py  —  v0.3.0
====================
Read and visualise IONEX ionospheric TEC maps as xarray Datasets.

Author : Bhuvnesh Brawar  <bbrawar@gmail.com>
         IIT Indore, Space Technology & Radio Cosmology Group

Changelog
---------
v0.3.0
  * BUG FIX  — latitude / longitude grids are now parsed directly from the
               IONEX header (LAT1/LAT2/DLAT, LON1/LON2/DLON/HGT) instead of
               being hardcoded.  Fixes silent wrong-value errors with CODE,
               ESA, and any non-JPL product.
  * BUG FIX  — files with no RMS maps (common in older IGS products) no
               longer crash; an all-NaN RMS array is returned and a warning
               is issued.
  * BUG FIX  — plt.rc(dict) → plt.rcParams.update() (TypeError fix).
  * BUG FIX  — double-backslash in ylabel raw strings corrected.
  * BUG FIX  — get_epoch() now uses a targeted regex instead of splitting
               on all whitespace before the tag; guards against non-numeric
               text in the header block.
  * BUG FIX  — geomag.GeoMag() is now instantiated once per call, not once
               per grid point (was 3 400+ file-loads per plot).
  * BUG FIX  — _base_map_fig extent is now derived from the actual grid.
  * FEATURE  — read_metadata=False default (opt-in for faster reads).
  * FEATURE  — Day/night terminator overlay with optional night shading
               (pure numpy, no extra dependencies).
  * FEATURE  — Geomagnetic latitude lines with labelled equator and ±30°
               magnetic latitude contours highlighted (requires geomag pkg).
  * FEATURE  — get_grid() exposed as public helper.
  * QUALITY  — All plot functions return (fig, ax) for downstream customisation.
  * QUALITY  — _base_map_fig extent driven by actual parsed grid bounds.

v0.2.x  (intermediate fixes, see git log)
v0.1.0  Initial release
"""

import warnings
import re
from datetime import datetime, timedelta

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import xarray as xr
import cartopy.crs as ccrs
from mpl_toolkits.axes_grid1 import make_axes_locatable

__version__ = '0.3.0'
__author__  = 'Bhuvnesh Brawar'
__email__   = 'bbrawar@gmail.com'

# ---------------------------------------------------------------------------
# CBAR label — defined once, used in multiple plot functions
# ---------------------------------------------------------------------------
_CBAR_LABEL = r'TECU  ($10^{16}\ \mathrm{el}\ \mathrm{m}^{-2}$)'


# ===========================================================================
# 1.  GRID PARSING  (v0.3.0 — replaces hardcoded linspace)
# ===========================================================================

def get_grid(header):
    """
    Parse the lat/lon/height grid specification from an IONEX file header.

    The header contains lines like::

        -87.5  87.5   5.0             LAT1 / LAT2 / DLAT
        -180.0 180.0  5.0             LON1 / LON2 / DLON

    This function reads them and returns the actual coordinate arrays so
    the Dataset has correct axes regardless of the agency that produced the
    file (JPL, CODE, ESA, CAS, …).

    Parameters
    ----------
    header : str
        IONEX header block (from :func:`_extract_header`).

    Returns
    -------
    latitudes : np.ndarray
        1-D array of geographic latitudes in degrees, from LAT1 to LAT2
        (may be descending, as is standard for IONEX — LAT1 > LAT2).
    longitudes : np.ndarray
        1-D array of geographic longitudes in degrees, from LON1 to LON2.
    heights : np.ndarray
        1-D array of ionospheric shell heights in km.

    Raises
    ------
    ValueError
        If the required header records are absent from the file.
    """
    # --- latitude ---
    lat_match = re.search(
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+LAT1 / LAT2 / DLAT', header
    )
    if not lat_match:
        raise ValueError(
            "LAT1 / LAT2 / DLAT record not found in IONEX header. "
            "Is this a valid IONEX file?"
        )
    lat1, lat2, dlat = (float(lat_match.group(i)) for i in (1, 2, 3))

    # --- longitude ---
    lon_match = re.search(
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+LON1 / LON2 / DLON',
        header,
    )
    if not lon_match:
        raise ValueError(
            "LON1 / LON2 / DLON record not found in IONEX header."
        )
    lon1, lon2, dlon = (float(lon_match.group(i)) for i in (1, 2, 3))

    # --- height (HGT1 / HGT2 / DHGT) — optional for 2-D IONEX ---
    hgt_match = re.search(
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+HGT1 / HGT2 / DHGT', header
    )
    if hgt_match:
        hgt1, hgt2, dhgt = (float(hgt_match.group(i)) for i in (1, 2, 3))
        n_hgt = max(1, round(abs(hgt2 - hgt1) / dhgt) + 1) if dhgt != 0 else 1
        heights = np.linspace(hgt1, hgt2, n_hgt)
    else:
        heights = np.array([hgt1])   # single shell from LON line

    # Build coordinate arrays — use round() to avoid floating-point drift
    # in np.arange, which can produce an extra spurious point.
    n_lat = max(1, round(abs(lat2 - lat1) / abs(dlat)) + 1)
    n_lon = max(1, round(abs(lon2 - lon1) / abs(dlon)) + 1)

    latitudes  = np.linspace(lat1, lat2, n_lat)
    longitudes = np.linspace(lon1, lon2, n_lon)

    return latitudes, longitudes, heights


# ===========================================================================
# 2.  PARSERS
# ===========================================================================

def get_epoch(block):
    """
    Extract the epoch datetime from a single TEC or RMS map block.

    Handles the IONEX special case where ``hour == 24`` represents midnight
    of the *next* day (24:00:00 → next-day 00:00:00).

    Parameters
    ----------
    block : str
        Raw text of a map block (everything after ``START OF TEC MAP``).

    Returns
    -------
    datetime
    """
    # Target exactly the six integers on the epoch line, ignore surrounding text
    m = re.search(
        r'^\s*(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})'
        r'\s+EPOCH OF CURRENT MAP',
        block, re.MULTILINE,
    )
    if not m:
        raise ValueError("Could not parse EPOCH OF CURRENT MAP from map block.")

    year, month, day, hour, minute, second = (int(m.group(i)) for i in range(1, 7))

    if hour == 24:
        return datetime(year, month, day, 0, minute, second) + timedelta(days=1)
    return datetime(year, month, day, hour, minute, second)


def parse_map(block, exponent=-1):
    """
    Parse a TEC map block into a 2-D numpy array.

    Parameters
    ----------
    block : str
        Raw text after ``START OF TEC MAP``.
    exponent : int
        Scaling exponent for raw integer values (default ``-1`` → ×0.1 TECU).

    Returns
    -------
    np.ndarray, shape (n_lat, n_lon)

    Raises
    ------
    ValueError
        If no latitude rows are found, or if rows have inconsistent lengths.
    """
    body = re.split(r'.*END OF TEC MAP', block)[0]
    rows = re.split(r'.*LAT/LON1/LON2/DLON/H\n', body)[1:]

    if not rows:
        raise ValueError("No latitude rows found in TEC map block.")

    arrays = [np.fromstring(r, sep=' ') for r in rows if r.strip()]
    _check_row_shapes(arrays, 'TEC')
    return np.stack(arrays) * 10**exponent


def parse_rms_map(block, exponent=-1):
    """
    Parse an RMS map block into a 2-D numpy array.

    Parameters
    ----------
    block : str
        Raw text after ``START OF RMS MAP``.
    exponent : int
        Scaling exponent (default ``-1`` → ×0.1 TECU).

    Returns
    -------
    np.ndarray, shape (n_lat, n_lon)
    """
    body = re.split(r'.*END OF RMS MAP', block)[0]
    rows = re.split(r'.*LAT/LON1/LON2/DLON/H\n', body)[1:]

    if not rows:
        raise ValueError("No latitude rows found in RMS map block.")

    arrays = [np.fromstring(r, sep=' ') for r in rows if r.strip()]
    _check_row_shapes(arrays, 'RMS')
    return np.stack(arrays) * 10**exponent


def _check_row_shapes(arrays, label):
    """Raise a clear error if latitude rows have inconsistent column counts."""
    lengths = [a.size for a in arrays]
    if len(set(lengths)) > 1:
        raise ValueError(
            f"{label} map has rows with inconsistent lengths: {set(lengths)}. "
            "The file may be truncated or malformed."
        )


def _extract_header(ionex_str):
    """
    Return only the header block of an IONEX file (everything up to and
    including the ``END OF HEADER`` line).

    The IONEX specification mandates this sentinel, so splitting on it is
    both correct and fast — the header is typically < 50 lines regardless
    of how many TEC/RMS maps the file contains.

    Parameters
    ----------
    ionex_str : str
        Full IONEX file contents.

    Returns
    -------
    str
        Header text only.  If the sentinel is absent (malformed file) the
        full string is returned as a fallback so callers still work.
    """
    sentinel = 'END OF HEADER'
    idx = ionex_str.find(sentinel)
    if idx == -1:
        warnings.warn(
            "'END OF HEADER' not found — file may be malformed. "
            "Falling back to scanning the full file for header records.",
            UserWarning,
        )
        return ionex_str
    # Include the sentinel line itself
    end = ionex_str.index('\n', idx) + 1
    return ionex_str[:end]


def get_metadata(header):
    """
    Extract optional metadata from an IONEX **header** string.

    Only called when ``read_ionex(..., read_metadata=True)``.
    Accepts the pre-sliced header (from :func:`_extract_header`) so regex
    scanning is limited to the small header block rather than the full file.

    Parameters
    ----------
    header : str
        IONEX header text (everything up to ``END OF HEADER``).

    Returns
    -------
    dict
        Keys ``'ionex_version'`` and ``'run_by'`` when found.
    """
    metadata = {}

    m = re.search(
        r'([\d.]+)\s+IONOSPHERE MAPS\s+\S+\s+IONEX VERSION / TYPE', header
    )
    if m:
        metadata['ionex_version'] = m.group(1)

    m = re.search(
        r'(.+?)\s{2,}(.+?)\s{2,}[\d]{2}-[A-Z]{3}-[\d]{2}.*PGM / RUN BY / DATE',
        header,
    )
    if m:
        metadata['run_by'] = m.group(2).strip()

    return metadata


# ===========================================================================
# 3.  CORE READER
# ===========================================================================

def read_ionex(filename, read_metadata=False):
    """
    Read an IONEX file and return an xarray Dataset.

    The dataset contains:

    * ``tec`` — Vertical TEC in TECU, dims (time, latitude, longitude).
    * ``rms`` — RMS of VTEC in TECU, dims (time, latitude, longitude).
      If the file contains no RMS maps a NaN-filled array is returned and a
      ``UserWarning`` is issued.

    Latitude and longitude coordinates are read directly from the file header
    (LAT1/LAT2/DLAT and LON1/LON2/DLON) so the Dataset is correct for any
    IONEX-producing agency (JPL 5°, CODE 2.5°, ESA 2.5°, …).

    Parameters
    ----------
    filename : str
        Path to the IONEX file (plain text, not compressed).
    read_metadata : bool, optional
        If ``True``, parse and attach ``ionex_version`` and ``run_by`` as
        Dataset attributes.  Defaults to ``False`` for faster reads.

    Returns
    -------
    xr.Dataset
    """
    with open(filename, encoding='utf-8', errors='replace') as f:
        ionex_str = f.read()

    # Extract header once — all header-only parsing uses this small slice.
    # get_grid and get_metadata never see the map data blocks.
    header = _extract_header(ionex_str)

    # --- grid (v0.3.0: read from header, not hardcoded) ---
    latitudes, longitudes, _ = get_grid(header)

    # --- TEC maps (required) ---
    tec_blocks = ionex_str.split('START OF TEC MAP')[1:]
    if not tec_blocks:
        raise ValueError(f"No TEC maps found in '{filename}'.")

    tecmaps = []
    epochs  = []
    for block in tec_blocks:
        try:
            tecmaps.append(parse_map(block))
            epochs.append(get_epoch(block))
        except (ValueError, IndexError) as exc:
            warnings.warn(f"Skipping malformed TEC block: {exc}", UserWarning)

    # --- RMS maps (optional) ---
    rms_blocks = ionex_str.split('START OF RMS MAP')[1:]
    if rms_blocks:
        rmsmaps = []
        for block in rms_blocks:
            try:
                rmsmaps.append(parse_rms_map(block))
            except (ValueError, IndexError) as exc:
                warnings.warn(f"Skipping malformed RMS block: {exc}", UserWarning)
    else:
        warnings.warn(
            f"'{filename}' contains no RMS maps. "
            "The 'rms' variable will be all-NaN.",
            UserWarning,
        )
        shape = (len(tecmaps), len(latitudes), len(longitudes))
        rmsmaps = [np.full((len(latitudes), len(longitudes)), np.nan)] * len(tecmaps)

    # Align lengths (guard against partially malformed files)
    n = min(len(tecmaps), len(rmsmaps), len(epochs))
    tecmaps, rmsmaps, epochs = tecmaps[:n], rmsmaps[:n], epochs[:n]

    metadata = get_metadata(header)    if read_metadata else {}
    return _create_xarray(tecmaps, rmsmaps, epochs, latitudes, longitudes, metadata)


# ===========================================================================
# 4.  XARRAY BUILDER  (private)
# ===========================================================================

def _create_xarray(tecmaps, rmsmaps, epochs, latitudes, longitudes, metadata):
    """Assemble parsed maps into an xr.Dataset."""
    ds = xr.Dataset(
        {
            'tec': (['time', 'latitude', 'longitude'], np.stack(tecmaps)),
            'rms': (['time', 'latitude', 'longitude'], np.stack(rmsmaps)),
        },
        coords={
            'time':      epochs,
            'latitude':  latitudes,
            'longitude': longitudes,
        },
    )
    ds['tec'].attrs.update(units='TECU', long_name='Vertical Total Electron Content')
    ds['rms'].attrs.update(units='TECU', long_name='RMS of Vertical TEC')
    ds.attrs['ionex_reader_version'] = __version__

    if metadata:
        ds.attrs.update(metadata)

    return ds


# ===========================================================================
# 5.  DAY / NIGHT TERMINATOR  (pure numpy — no extra dependencies)
# ===========================================================================

def _subsolar_point(dt):
    """
    Compute subsolar latitude and longitude for a UTC datetime.

    Uses the Astronomical Almanac low-precision solar coordinate model
    (~0.5° accuracy over a few decades around J2000), which is well within
    the resolution of any global TEC map.

    Parameters
    ----------
    dt : datetime (UTC)

    Returns
    -------
    lat_sun, lon_sun : float, float  (degrees)
    """
    jd = (
        367 * dt.year
        - int(7 * (dt.year + int((dt.month + 9) / 12)) / 4)
        + int(275 * dt.month / 9)
        + dt.day + 1721013.5
        + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    )
    T  = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + 36000.76983 * T) % 360
    M  = np.radians((357.52911 + 35999.05029 * T - 0.0001537 * T**2) % 360)
    C  = ((1.914602 - 0.004817 * T - 0.000014 * T**2) * np.sin(M)
          + (0.019993 - 0.000101 * T) * np.sin(2 * M)
          + 0.000289 * np.sin(3 * M))

    omega   = np.radians(125.04 - 1934.136 * T)
    lam     = np.radians(L0 + C - 0.00569 - 0.00478 * np.sin(omega))
    eps     = np.radians(23.439291 - 0.013004 * T + 0.00256 * np.cos(omega))
    lat_sun = np.degrees(np.arcsin(np.sin(eps) * np.sin(lam)))

    gmst    = (280.46061837
               + 360.98564736629 * (jd - 2451545.0)
               + 0.000387933 * T**2
               - T**3 / 38710000) % 360
    ra_sun  = np.degrees(np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))) % 360
    lon_sun = (ra_sun - gmst + 180) % 360 - 180

    return lat_sun, lon_sun


def _plot_terminator(ax, dt,
                     line_color='white', line_width=1.5,
                     night_color='navy', night_alpha=0.25,
                     show_night_shade=True):
    """
    Draw the day/night terminator on a Cartopy PlateCarree axes.

    The terminator is the locus where the solar zenith angle equals 90°,
    computed as::

        cos Z = sin φ sin δ  +  cos φ cos δ cos H

    where φ is geographic latitude, δ is solar declination, and H is the
    solar hour angle (longitude − subsolar longitude).

    Parameters
    ----------
    ax : cartopy GeoAxes  (PlateCarree projection)
    dt : datetime (UTC)
        Epoch for solar position.  Pass ``None`` to skip silently.
    line_color : str     Terminator line colour  (default ``'white'``).
    line_width : float   Line width              (default ``1.5``).
    night_color : str    Night-side fill colour  (default ``'navy'``).
    night_alpha : float  Night-side opacity      (default ``0.25``).
    show_night_shade : bool
        Shade the night hemisphere (default ``True``).
    """
    if dt is None:
        return

    lat_sun, lon_sun = _subsolar_point(dt)

    lons = np.linspace(-180, 180, 721)
    lats = np.linspace(-90,   90, 361)
    LON, LAT = np.meshgrid(lons, lats)

    cos_sza = (np.sin(np.radians(LAT)) * np.sin(np.radians(lat_sun))
               + np.cos(np.radians(LAT)) * np.cos(np.radians(lat_sun))
               * np.cos(np.radians(LON - lon_sun)))

    proj = ccrs.PlateCarree()

    if show_night_shade:
        ax.contourf(lons, lats, cos_sza, levels=[-1, 0],
                    colors=[night_color], alpha=night_alpha, transform=proj)

    ax.contour(lons, lats, cos_sza, levels=[0],
               colors=[line_color], linewidths=line_width, transform=proj)


def _epoch_to_datetime(data):
    """
    Extract a Python datetime from an xr.DataArray ``time`` coordinate.

    Returns ``None`` on failure so callers can emit a clean warning.
    """
    try:
        import pandas as pd
        return pd.Timestamp(data.time.values).to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None


# ===========================================================================
# 6.  GEOMAGNETIC LATITUDE LINES  (deferred import)
# ===========================================================================

def _plot_geomagnetic_latitude_lines(ax,
                                     step_deg=10,
                                     highlight_lats=(-30, 0, 30),
                                     label_lats=(-60, -30, 0, 30, 60),
                                     line_color='red',
                                     line_alpha=0.65,
                                     line_width=0.8,
                                     highlight_width=1.6):
    """
    Overlay geomagnetic (dip) latitude lines on an existing Cartopy axes.

    Geomagnetic latitude is derived from the magnetic dip (inclination) angle
    returned by the World Magnetic Model via the ``geomag`` package::

        mag_lat = arctan(0.5 × tan(dip))

    Strategy (vectorised, ~2 s total):

    1. Build a dense geographic lat × lon grid of magnetic latitudes in one
       pass (``geomag.geomag.GeoMag`` instantiated **once**).
    2. Pass the full grid to ``ax.contour()`` which extracts all desired
       magnetic-latitude isolines simultaneously — no per-contour loop.
    3. Add styled labels for lines listed in *label_lats*.

    Import note
    -----------
    ``GeoMag`` lives at ``geomag.geomag.GeoMag``, not ``geomag.GeoMag``.
    The package is imported lazily so it does not slow down imports when this
    feature is unused.

    Parameters
    ----------
    ax : cartopy GeoAxes  (PlateCarree projection)
    step_deg : int
        Spacing between geomagnetic latitude contours in degrees (default 10).
    highlight_lats : tuple of float
        Magnetic latitudes drawn thicker and fully opaque
        (default: −30°, magnetic equator 0°, +30°  — i.e. the EIA boundaries).
    label_lats : tuple of float
        Magnetic latitudes annotated with a text label (default: ±60, ±30, 0°).
    line_color : str
        Colour for all geomagnetic lines (default ``'red'``).
    line_alpha : float
        Opacity for regular (non-highlighted) lines (default 0.65).
    line_width : float
        Line width for regular lines (default 0.8).
    highlight_width : float
        Line width for highlighted lines (default 1.6).

    Raises
    ------
    ImportError
        If the ``geomag`` package is not installed
        (``pip install geomag``).
    """
    try:
        from geomag.geomag import GeoMag          # correct import path
    except ImportError:
        raise ImportError(
            "The 'geomag' package is required for geomagnetic latitude lines.\n"
            "Install it with:  pip install geomag"
        )

    proj = ccrs.PlateCarree()

    # ------------------------------------------------------------------
    # Step 1 — build a (geo_lat × lon) grid of magnetic dip-latitudes.
    # GeoMag is instantiated ONCE here (loads WMM file from disk once).
    # Grid resolution: 2.5° lat × 5° lon → 73 × 72 = 5 256 points, ~0.7 s.
    # ------------------------------------------------------------------
    gm       = GeoMag()
    lons     = np.arange(-180, 180,  5.0)
    geo_lats = np.arange( -90,  91,  2.5)

    mag_lat_grid = np.empty((len(geo_lats), len(lons)), dtype=np.float32)
    for i, glat in enumerate(geo_lats):
        for j, lon in enumerate(lons):
            dip = gm.GeoMag(glat, lon).dip
            mag_lat_grid[i, j] = np.degrees(np.arctan(0.5 * np.tan(np.radians(dip))))

    # ------------------------------------------------------------------
    # Step 2 — define contour levels covering the requested range
    # ------------------------------------------------------------------
    lat_min = int(np.floor(geo_lats[0]  / step_deg) * step_deg)
    lat_max = int(np.ceil (geo_lats[-1] / step_deg) * step_deg)
    all_levels    = np.arange(lat_min, lat_max + 1, step_deg).tolist()
    hi_set        = set(highlight_lats)
    label_set     = set(label_lats)

    # ------------------------------------------------------------------
    # Step 3 — draw regular lines via contour (one matplotlib call)
    # ------------------------------------------------------------------
    regular_levels = [lv for lv in all_levels if lv not in hi_set]
    if regular_levels:
        ax.contour(
            lons, geo_lats, mag_lat_grid,
            levels=regular_levels,
            colors=[line_color],
            linewidths=line_width,
            linestyles='--',
            alpha=line_alpha,
            transform=proj,
            zorder=4,
        )

    # ------------------------------------------------------------------
    # Step 4 — draw highlighted lines (thicker, solid, fully opaque)
    # ------------------------------------------------------------------
    hi_levels = [lv for lv in all_levels if lv in hi_set]
    if hi_levels:
        ax.contour(
            lons, geo_lats, mag_lat_grid,
            levels=hi_levels,
            colors=[line_color],
            linewidths=highlight_width,
            linestyles='-',
            alpha=1.0,
            transform=proj,
            zorder=4,
        )

    # ------------------------------------------------------------------
    # Step 5 — add text labels at ~150 °E for selected latitudes
    # ------------------------------------------------------------------
    label_lon  = 150.0
    lon_idx    = np.argmin(np.abs(lons - label_lon))

    for target in label_set:
        # Find the geographic latitude whose magnetic latitude is closest
        # to the target at the label longitude
        col     = mag_lat_grid[:, lon_idx]
        geo_idx = int(np.argmin(np.abs(col - target)))
        geo_lat_at_label = float(geo_lats[geo_idx])

        sign = '+' if target > 0 else ('' if target == 0 else '')
        is_hi = target in hi_set
        ax.text(
            label_lon,
            geo_lat_at_label,
            f'{sign}{int(target)}°',
            transform=proj,
            color=line_color,
            fontsize=7,
            fontweight='bold' if is_hi else 'normal',
            va='bottom',
            ha='center',
            path_effects=[pe.withStroke(linewidth=2, foreground='white')],
            zorder=5,
        )


# ===========================================================================
# 7.  MAP PLOTTING HELPERS
# ===========================================================================

def _map_extent(ds):
    """Return the imshow/map extent (lon_min, lon_max, lat_min, lat_max)
    from the Dataset coordinates so the extent always matches the actual grid."""
    lon = ds.longitude.values if hasattr(ds, 'longitude') else np.array([-180, 180])
    lat = ds.latitude.values  if hasattr(ds, 'latitude')  else np.array([-90,   90])
    # Half-cell padding so pixels are centred on their coordinate
    dlon = abs(float(lon[1] - lon[0])) / 2 if lon.size > 1 else 0
    dlat = abs(float(lat[1] - lat[0])) / 2 if lat.size > 1 else 0
    return (float(lon[0]) - dlon, float(lon[-1]) + dlon,
            float(min(lat[0], lat[-1])) - dlat,
            float(max(lat[0], lat[-1])) + dlat)


def _base_map_fig(data, cmap, vmin, vmax, title, cbar_label, extent):
    """Shared map-setup logic for TEC and RMS maps."""
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj), figsize=(12, 5))
    ax.coastlines(resolution='110m', linewidth=0.8)
    ax.add_feature(__import__('cartopy.feature', fromlist=['BORDERS']).BORDERS,
                   linewidth=0.4, alpha=0.6)

    h = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax,
                  extent=extent, transform=proj, origin='upper')

    gl = ax.gridlines(draw_labels=True, linewidth=0.8, color='gray',
                      alpha=0.5, linestyle='--')
    gl.top_labels   = False
    gl.right_labels = False

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(title, pad=8)

    divider = make_axes_locatable(ax)
    ax_cb   = divider.new_horizontal(size='3%', pad=0.08, axes_class=plt.Axes)
    fig.add_axes(ax_cb)
    plt.colorbar(h, cax=ax_cb, label=cbar_label)

    fig.tight_layout()
    return fig, ax


def plot_tec_map(tecmap,
                 add_geomagnetic_lines=False,
                 geomag_kw=None,
                 add_terminator=False,
                 terminator_dt=None,
                 terminator_kw=None):
    """
    Plot a Vertical TEC map.

    Parameters
    ----------
    tecmap : xr.DataArray or np.ndarray
        2-D TEC map, shape (n_lat, n_lon).  Passing an xr.DataArray is
        recommended so the epoch and grid are inferred automatically.
    add_geomagnetic_lines : bool
        Overlay geomagnetic latitude lines.  Requires the ``geomag`` package
        (``pip install geomag``).  See *geomag_kw* for styling options.
    geomag_kw : dict or None
        Keyword arguments forwarded to :func:`_plot_geomagnetic_latitude_lines`.
        Examples::

            geomag_kw=dict(step_deg=10, highlight_lats=(0,), line_color='orange')

    add_terminator : bool
        Overlay the day/night terminator.  The epoch is inferred from
        ``tecmap.time`` when available; supply *terminator_dt* for plain
        numpy arrays.
    terminator_dt : datetime or None
        Override the UTC epoch for the terminator.
    terminator_kw : dict or None
        Keyword arguments forwarded to :func:`_plot_terminator`.  Examples::

            terminator_kw=dict(night_alpha=0.35, line_color='yellow')
            terminator_kw=dict(show_night_shade=False, line_color='red')

    Returns
    -------
    fig, ax : matplotlib Figure and Axes
    """
    try:
        title = f'VTEC map  —  {np.datetime_as_string(tecmap.time.values, unit="m")} UTC'
    except Exception:
        title = 'VTEC map'

    # Derive extent from DataArray coords if possible
    try:
        lons = tecmap.longitude.values
        lats = tecmap.latitude.values
        dlon = abs(lons[1] - lons[0]) / 2
        dlat = abs(lats[1] - lats[0]) / 2
        extent = (lons[0] - dlon, lons[-1] + dlon,
                  min(lats[-1], lats[0]) - dlat,
                  max(lats[-1], lats[0]) + dlat)
    except Exception:
        extent = (-182.5, 182.5, -90, 90)

    fig, ax = _base_map_fig(
        tecmap, cmap='viridis', vmin=0, vmax=100,
        title=title, cbar_label=_CBAR_LABEL, extent=extent,
    )

    if add_geomagnetic_lines:
        _plot_geomagnetic_latitude_lines(ax, **(geomag_kw or {}))

    if add_terminator:
        dt = terminator_dt or _epoch_to_datetime(tecmap)
        if dt is None:
            warnings.warn(
                "add_terminator=True but no epoch found. "
                "Pass terminator_dt=<datetime>.", UserWarning
            )
        else:
            _plot_terminator(ax, dt, **(terminator_kw or {}))

    return fig, ax


def plot_rms_map(rmsmap,
                 add_geomagnetic_lines=False,
                 geomag_kw=None,
                 add_terminator=False,
                 terminator_dt=None,
                 terminator_kw=None):
    """
    Plot a TEC RMS map.

    Parameters
    ----------
    rmsmap : xr.DataArray or np.ndarray
        2-D RMS map, shape (n_lat, n_lon).
    add_geomagnetic_lines : bool
        Overlay geomagnetic latitude lines (requires ``geomag`` package).
    geomag_kw : dict or None
        Styling options for geomagnetic lines (see :func:`plot_tec_map`).
    add_terminator : bool
        Overlay the day/night terminator.
    terminator_dt : datetime or None
        Override UTC epoch for the terminator.
    terminator_kw : dict or None
        Styling options for the terminator (see :func:`plot_tec_map`).

    Returns
    -------
    fig, ax : matplotlib Figure and Axes
    """
    try:
        title = f'TEC RMS map  —  {np.datetime_as_string(rmsmap.time.values, unit="m")} UTC'
    except Exception:
        title = 'TEC RMS map'

    try:
        lons = rmsmap.longitude.values
        lats = rmsmap.latitude.values
        dlon = abs(lons[1] - lons[0]) / 2
        dlat = abs(lats[1] - lats[0]) / 2
        extent = (lons[0] - dlon, lons[-1] + dlon,
                  min(lats[-1], lats[0]) - dlat,
                  max(lats[-1], lats[0]) + dlat)
    except Exception:
        extent = (-182.5, 182.5, -90, 90)

    fig, ax = _base_map_fig(
        rmsmap, cmap='plasma', vmin=0, vmax=10,
        title=title, cbar_label=_CBAR_LABEL, extent=extent,
    )

    if add_geomagnetic_lines:
        _plot_geomagnetic_latitude_lines(ax, **(geomag_kw or {}))

    if add_terminator:
        dt = terminator_dt or _epoch_to_datetime(rmsmap)
        if dt is None:
            warnings.warn(
                "add_terminator=True but no epoch found. "
                "Pass terminator_dt=<datetime>.", UserWarning
            )
        else:
            _plot_terminator(ax, dt, **(terminator_kw or {}))

    return fig, ax


# ===========================================================================
# 8.  TIME-SERIES PLOT
# ===========================================================================

def plot_time_series(ds, lat, lon, variable='tec'):
    """
    Plot the time series of TEC or RMS at the nearest grid point to (lat, lon).

    Parameters
    ----------
    ds : xr.Dataset
        Dataset returned by :func:`read_ionex`.
    lat : float
        Target latitude (degrees).  Snapped to nearest grid point.
    lon : float
        Target longitude (degrees).  Snapped to nearest grid point.
    variable : {'tec', 'rms'}
        Which variable to plot.

    Returns
    -------
    fig, ax : matplotlib Figure and Axes
    """
    if variable not in ds:
        raise ValueError(f"Variable '{variable}' not in dataset. Choose 'tec' or 'rms'.")

    lat_idx = int(np.abs(ds.latitude  - lat).argmin())
    lon_idx = int(np.abs(ds.longitude - lon).argmin())

    actual_lat = float(ds.latitude[lat_idx])
    actual_lon = float(ds.longitude[lon_idx])

    if actual_lat != lat or actual_lon != lon:
        warnings.warn(
            f"Requested ({lat}°, {lon}°) snapped to nearest grid point "
            f"({actual_lat}°, {actual_lon}°).",
            UserWarning,
        )

    ts = ds[variable].isel(latitude=lat_idx, longitude=lon_idx)

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(ds.time.values, ts.values, marker='o', markersize=3, linewidth=1.4,
            label=f'{variable.upper()} at ({actual_lat}°, {actual_lon}°)')
    ax.set_xlabel('Time (UTC)')
    ax.set_ylabel(r'TECU  ($10^{16}\ \mathrm{el}\ \mathrm{m}^{-2}$)')
    ax.set_title(
        f'Time Series of {variable.upper()}  —  ({actual_lat}°N, {actual_lon}°E)'
    )
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.4)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig, ax


# ===========================================================================
# 9.  EXAMPLE USAGE
# ===========================================================================
#
# ---------- Read ------------------------------------------------------------
# ds = read_ionex('igsg0010.24i')                      # fast — no metadata
# ds = read_ionex('igsg0010.24i', read_metadata=True)  # attach header info
# print(ds)                 # shows actual lat/lon grid from the file header
# print(ds.attrs)           # ionex_version, run_by (if read_metadata=True)
#
# ---------- Inspect grid (v0.3.0) ------------------------------------------
# lats, lons, heights = get_grid(open('igsg0010.24i').read())
# print(f'Lat: {lats[0]}°  →  {lats[-1]}°  step {abs(lats[1]-lats[0])}°')
# print(f'Lon: {lons[0]}°  →  {lons[-1]}°  step {abs(lons[1]-lons[0])}°')
#
# ---------- Basic maps ------------------------------------------------------
# fig, ax = plot_tec_map(ds['tec'].isel(time=0))
# fig, ax = plot_rms_map(ds['rms'].isel(time=6))
#
# ---------- Terminator overlay ----------------------------------------------
# fig, ax = plot_tec_map(ds['tec'].isel(time=6), add_terminator=True)
#
# fig, ax = plot_tec_map(
#     ds['tec'].isel(time=6),
#     add_terminator=True,
#     terminator_kw=dict(night_alpha=0.35, line_color='yellow', line_width=2),
# )
#
# # Plain numpy array — epoch must be supplied manually
# from datetime import datetime
# fig, ax = plot_tec_map(
#     ds['tec'].isel(time=0).values,
#     add_terminator=True,
#     terminator_dt=datetime(2024, 1, 1, 12, 0, 0),
# )
#
# ---------- Geomagnetic latitude lines (requires: pip install geomag) -------
# # Default: ±10° steps, equator + ±30° highlighted, labels at ±60,±30,0°
# fig, ax = plot_tec_map(ds['tec'].isel(time=6), add_geomagnetic_lines=True)
#
# # Custom spacing and colours
# fig, ax = plot_tec_map(
#     ds['tec'].isel(time=6),
#     add_geomagnetic_lines=True,
#     geomag_kw=dict(
#         step_deg=10,
#         highlight_lats=(-30, 0, 30),   # magnetic equator + ±EIA latitudes
#         label_lats=(-60, -30, 0, 30, 60),
#         line_color='tomato',
#         line_alpha=0.7,
#         line_width=0.9,
#         highlight_width=2.0,
#     ),
# )
#
# ---------- All overlays combined -------------------------------------------
# fig, ax = plot_tec_map(
#     ds['tec'].isel(time=6),
#     add_terminator=True,
#     terminator_kw=dict(night_alpha=0.30, line_color='white'),
#     add_geomagnetic_lines=True,
#     geomag_kw=dict(step_deg=10, line_color='red'),
# )
#
# ---------- Time series at IIT Indore ---------------------------------------
# fig, ax = plot_time_series(ds, lat=22.5, lon=75.5, variable='tec')
#
# plt.show()
