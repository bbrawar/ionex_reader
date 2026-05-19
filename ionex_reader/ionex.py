import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime, timedelta
import xarray as xr
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs

'''
IONEX file reader as xarray Datasets.
email: bbrawar@gmail.com

Changelog:
- Metadata extraction is now optional (default: False) for faster reads.
- Only TEC and RMS maps are returned by default.
- geomag import is deferred to avoid overhead when not plotting geomag lines.
- Day/night terminator overlay added (no extra dependencies — pure numpy math).
'''


# ---------------------------------------------------------------------------
# Core reader
# ---------------------------------------------------------------------------

def read_ionex(filename, read_metadata=False):
    """
    Read an IONEX file and extract TEC maps, RMS maps, epochs, and optionally metadata.

    Parameters
    ----------
    filename : str
        Path to the IONEX file.
    read_metadata : bool, optional
        If True, parse and attach file metadata (version, run_by) to the dataset.
        Defaults to False for faster reads.

    Returns
    -------
    xr.Dataset
        Dataset containing TEC and RMS maps with time/lat/lon coordinates.
        Metadata attributes are only populated when read_metadata=True.
    """
    with open(filename) as f:
        ionex = f.read()

    tecmaps = [parse_map(t)     for t in ionex.split('START OF TEC MAP')[1:]]
    rmsmaps = [parse_rms_map(t) for t in ionex.split('START OF RMS MAP')[1:]]
    epochs  = [get_epoch(t)     for t in ionex.split('START OF TEC MAP')[1:]]

    metadata = get_metadata(ionex) if read_metadata else {}

    return _create_xarray(tecmaps, rmsmaps, epochs, metadata)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_map(tecmap, exponent=-1):
    """
    Parse a TEC map block into a numpy array.

    Parameters
    ----------
    tecmap : str
        Raw string of a single TEC map block (after 'START OF TEC MAP').
    exponent : int
        Scaling exponent applied to raw integer values (default -1 → ×0.1 TECU).

    Returns
    -------
    np.ndarray, shape (n_lat, n_lon)
    """
    tecmap = re.split(r'.*END OF TEC MAP', tecmap)[0]
    rows = re.split(r'.*LAT/LON1/LON2/DLON/H\n', tecmap)[1:]
    return np.stack([np.fromstring(row, sep=' ') for row in rows]) * 10**exponent


def parse_rms_map(rmsmap, exponent=-1):
    """
    Parse an RMS map block into a numpy array.

    Parameters
    ----------
    rmsmap : str
        Raw string of a single RMS map block (after 'START OF RMS MAP').
    exponent : int
        Scaling exponent applied to raw integer values (default -1 → ×0.1 TECU).

    Returns
    -------
    np.ndarray, shape (n_lat, n_lon)
    """
    rmsmap = re.split(r'.*END OF RMS MAP', rmsmap)[0]
    rows = re.split(r'.*LAT/LON1/LON2/DLON/H\n', rmsmap)[1:]
    return np.stack([np.fromstring(row, sep=' ') for row in rows]) * 10**exponent


def get_epoch(tecmap):
    """
    Extract the epoch datetime from a TEC map block.

    Handles the IONEX special case where hour=24 represents midnight of the
    next day (i.e. 24:00:00 → next day 00:00:00).

    Parameters
    ----------
    tecmap : str
        Raw string of a single TEC map block.

    Returns
    -------
    datetime
    """
    raw = re.split(r'EPOCH OF CURRENT MAP', tecmap)[0]
    year, month, day, hour, minute, second = np.array(raw.split(), dtype=int)

    if hour == 24:
        return datetime(year, month, day, 0, minute, second) + timedelta(days=1)
    return datetime(year, month, day, hour, minute, second)


def get_metadata(ionex):
    """
    Extract header metadata from the full IONEX file string.

    Only called when read_metadata=True; skipped by default to keep reads fast.

    Parameters
    ----------
    ionex : str
        Full IONEX file contents.

    Returns
    -------
    dict
        Keys: 'ionex_version', 'run_by'  (present only when found in header).
    """
    metadata = {}

    version_match = re.search(
        r'(\d+\.\d+)\s+IONOSPHERE MAPS\s+GNSS\s+IONEX VERSION / TYPE', ionex
    )
    if version_match:
        metadata['ionex_version'] = version_match.group(1)

    pgm_match = re.search(
        r'(.+?)\s+(.+?)\s+(\d{2}-[A-Z]{3}-\d{2} \d{2}:\d{2})\s+PGM / RUN BY / DATE',
        ionex,
    )
    if pgm_match:
        metadata['run_by'] = pgm_match.group(2).strip()

    return metadata


# ---------------------------------------------------------------------------
# xarray builder (private)
# ---------------------------------------------------------------------------

def _create_xarray(tecmaps, rmsmaps, epochs, metadata):
    """
    Assemble TEC and RMS arrays into an xr.Dataset.

    Parameters
    ----------
    tecmaps : list of np.ndarray
    rmsmaps : list of np.ndarray
    epochs  : list of datetime
    metadata : dict

    Returns
    -------
    xr.Dataset
    """
    n_lat, n_lon = tecmaps[0].shape
    latitudes  = np.linspace( 87.5, -87.5, n_lat)
    longitudes = np.linspace(-180,   180,  n_lon)

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
    ds['tec'].attrs['units'] = 'TECU'
    ds['tec'].attrs['long_name'] = 'Vertical Total Electron Content'
    ds['rms'].attrs['units'] = 'TECU'
    ds['rms'].attrs['long_name'] = 'RMS of Vertical TEC'

    if metadata:
        ds.attrs.update(metadata)

    return ds


# ---------------------------------------------------------------------------
# Day / Night terminator (pure numpy — no extra dependencies)
# ---------------------------------------------------------------------------

def _subsolar_point(dt):
    """
    Compute the subsolar latitude and longitude for a UTC datetime.

    Uses a low-precision solar position model accurate to ~0.5° for dates
    within a few decades of J2000 — more than sufficient for ionospheric maps.

    Algorithm
    ---------
    Based on the Astronomical Almanac low-precision solar coordinates
    (accurate to ~1 arcmin over ±5 centuries from J2000).

    Parameters
    ----------
    dt : datetime
        UTC datetime.

    Returns
    -------
    lat_sun : float
        Subsolar latitude (degrees), i.e. solar declination.
    lon_sun : float
        Subsolar longitude (degrees), i.e. negative of Greenwich Hour Angle.
    """
    # Julian date
    jd = (
        367 * dt.year
        - int(7 * (dt.year + int((dt.month + 9) / 12)) / 4)
        + int(275 * dt.month / 9)
        + dt.day
        + 1721013.5
        + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    )

    # Julian centuries from J2000.0
    T = (jd - 2451545.0) / 36525.0

    # Geometric mean longitude of the Sun (degrees), referred to mean equinox of date
    L0 = (280.46646 + 36000.76983 * T) % 360

    # Mean anomaly of the Sun (degrees)
    M = np.radians((357.52911 + 35999.05029 * T - 0.0001537 * T**2) % 360)

    # Equation of centre
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T**2) * np.sin(M)
        + (0.019993 - 0.000101 * T) * np.sin(2 * M)
        + 0.000289 * np.sin(3 * M)
    )

    # Sun's true longitude (degrees)
    sun_lon = L0 + C

    # Apparent longitude (correcting for aberration and nutation)
    omega = np.radians(125.04 - 1934.136 * T)
    lam   = np.radians(sun_lon - 0.00569 - 0.00478 * np.sin(omega))

    # Obliquity of the ecliptic (degrees)
    eps0  = 23.439291 - 0.013004 * T
    eps   = np.radians(eps0 + 0.00256 * np.cos(omega))

    # Solar declination
    lat_sun = np.degrees(np.arcsin(np.sin(eps) * np.sin(lam)))

    # Greenwich Mean Sidereal Time (degrees)
    gmst = (280.46061837
            + 360.98564736629 * (jd - 2451545.0)
            + 0.000387933 * T**2
            - T**3 / 38710000) % 360

    # Right ascension of the Sun
    ra_sun = np.degrees(np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))) % 360

    # Subsolar longitude = RA_sun − GMST  (both in degrees)
    lon_sun = (ra_sun - gmst + 180) % 360 - 180

    return lat_sun, lon_sun


def _plot_terminator(ax, dt,
                     line_color='white', line_width=1.5,
                     night_color='navy', night_alpha=0.25,
                     show_night_shade=True):
    """
    Draw the day/night terminator on an existing Cartopy PlateCarree axes.

    The terminator is the locus of points where the solar zenith angle equals
    exactly 90°.  The night hemisphere is optionally shaded.

    Uses the solar zenith angle formula:
        cos(Z) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(H)
    where φ = geographic latitude, δ = solar declination,
    H = hour angle = longitude − subsolar longitude.

    Parameters
    ----------
    ax : cartopy GeoAxes
        The axes to draw on (must use PlateCarree projection).
    dt : datetime
        UTC epoch for which to compute the terminator position.
        If None, no terminator is drawn and the function returns silently.
    line_color : str
        Colour of the terminator line (default 'white').
    line_width : float
        Line width (default 1.5).
    night_color : str
        Fill colour for the night-side shading (default 'navy').
    night_alpha : float
        Opacity of the night-side shading (0 = transparent, 1 = opaque).
    show_night_shade : bool
        If True (default), shade the night hemisphere in addition to
        drawing the terminator line.
    """
    if dt is None:
        return

    lat_sun, lon_sun = _subsolar_point(dt)

    # Build a dense regular grid for contour evaluation
    lons = np.linspace(-180, 180, 721)
    lats = np.linspace(-90,   90, 361)
    LON, LAT = np.meshgrid(lons, lats)

    # Hour angle (radians)
    H = np.radians(LON - lon_sun)

    # Cosine of solar zenith angle
    cos_sza = (
        np.sin(np.radians(LAT)) * np.sin(np.radians(lat_sun))
        + np.cos(np.radians(LAT)) * np.cos(np.radians(lat_sun)) * np.cos(H)
    )

    proj = ccrs.PlateCarree()

    # Night-side shading (cos_sza < 0  ↔  zenith angle > 90°)
    if show_night_shade:
        ax.contourf(
            lons, lats, cos_sza,
            levels=[-1, 0],
            colors=[night_color],
            alpha=night_alpha,
            transform=proj,
        )

    # Terminator line (cos_sza = 0)
    ax.contour(
        lons, lats, cos_sza,
        levels=[0],
        colors=[line_color],
        linewidths=line_width,
        transform=proj,
    )


def _epoch_to_datetime(data):
    """
    Extract a Python datetime from an xr.DataArray time coordinate.

    Returns None if the time coordinate is absent or conversion fails,
    allowing callers to decide whether to skip the terminator.
    """
    try:
        t = data.time.values
        # numpy datetime64 → Python datetime via pandas
        import pandas as pd
        return pd.Timestamp(t).to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _base_map_fig(data, cmap, vmin, vmax, title, cbar_label):
    """Shared map-setup logic for TEC and RMS maps."""
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj))
    ax.coastlines()

    h = ax.imshow(
        data, cmap=cmap, vmin=vmin, vmax=vmax,
        extent=(-180, 180, -87.5, 87.5), transform=proj,
    )

    gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray',
                      alpha=0.5, linestyle='--')
    gl.top_labels   = False
    gl.right_labels = False

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    plt.title(title)

    divider = make_axes_locatable(ax)
    ax_cb   = divider.new_horizontal(size='5%', pad=0.1, axes_class=plt.Axes)
    fig.add_axes(ax_cb)
    cb = plt.colorbar(h, cax=ax_cb)
    cb.set_label(cbar_label)

    return fig, ax


def plot_tec_map(tecmap, add_geomagnetic_lines=False,
                 add_terminator=False,
                 terminator_dt=None,
                 terminator_kw=None):
    """
    Plot a VTEC map.

    Parameters
    ----------
    tecmap : np.ndarray or xr.DataArray
        2-D TEC map (latitude × longitude).
    add_geomagnetic_lines : bool
        Overlay geomagnetic latitude lines (requires the ``geomag`` package).
    add_terminator : bool
        Overlay the day/night terminator.  When True, the epoch is taken
        automatically from ``tecmap.time`` if available; otherwise pass an
        explicit UTC datetime via *terminator_dt*.
    terminator_dt : datetime or None
        Override the epoch used for the terminator.  Useful when *tecmap* is
        a plain numpy array with no time coordinate.
    terminator_kw : dict or None
        Extra keyword arguments forwarded to :func:`_plot_terminator`
        (e.g. ``{'night_alpha': 0.35, 'line_color': 'yellow'}``).

    Returns
    -------
    fig, ax
    """
    try:
        title = f'VTEC map ({tecmap.time.values})'
    except AttributeError:
        title = 'VTEC map'

    fig, ax = _base_map_fig(
        tecmap, cmap='viridis', vmin=0, vmax=100,
        title=title,
        cbar_label=r'TECU ($10^{16}\ \mathrm{el}/\mathrm{m}^2$)',
    )

    if add_geomagnetic_lines:
        _plot_geomagnetic_latitude_lines(ax)

    if add_terminator:
        dt = terminator_dt or _epoch_to_datetime(tecmap)
        if dt is None:
            import warnings
            warnings.warn(
                "add_terminator=True but no epoch could be determined. "
                "Pass terminator_dt=<datetime> explicitly.", UserWarning
            )
        else:
            _plot_terminator(ax, dt, **(terminator_kw or {}))

    return fig, ax


def plot_rms_map(rmsmap, add_terminator=False,
                 terminator_dt=None,
                 terminator_kw=None):
    """
    Plot a TEC RMS map.

    Parameters
    ----------
    rmsmap : np.ndarray or xr.DataArray
        2-D RMS map (latitude × longitude).
    add_terminator : bool
        Overlay the day/night terminator.  Epoch is read from ``rmsmap.time``
        when available, or supplied via *terminator_dt*.
    terminator_dt : datetime or None
        Override epoch for the terminator.
    terminator_kw : dict or None
        Extra keyword arguments for :func:`_plot_terminator`.

    Returns
    -------
    fig, ax
    """
    try:
        title = f'RMS map ({rmsmap.time.values})'
    except AttributeError:
        title = 'RMS map'

    fig, ax = _base_map_fig(
        rmsmap, cmap='plasma', vmin=0, vmax=10,
        title=title,
        cbar_label=r'TECU ($10^{16}\ \mathrm{el}/\mathrm{m}^2$)',
    )

    if add_terminator:
        dt = terminator_dt or _epoch_to_datetime(rmsmap)
        if dt is None:
            import warnings
            warnings.warn(
                "add_terminator=True but no epoch could be determined. "
                "Pass terminator_dt=<datetime> explicitly.", UserWarning
            )
        else:
            _plot_terminator(ax, dt, **(terminator_kw or {}))

    return fig, ax


def plot_time_series(ds, lat, lon, variable='tec'):
    """
    Plot time series of TEC or RMS at a given lat/lon.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset returned by read_ionex().
    lat : float
        Latitude (degrees).
    lon : float
        Longitude (degrees).
    variable : {'tec', 'rms'}
        Variable to plot.
    """
    lat_idx = int(np.abs(ds.latitude  - lat).argmin())
    lon_idx = int(np.abs(ds.longitude - lon).argmin())

    actual_lat = float(ds.latitude[lat_idx])
    actual_lon = float(ds.longitude[lon_idx])

    time_series = ds[variable].isel(latitude=lat_idx, longitude=lon_idx)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ds.time.values, time_series.values,
            label=f'{variable.upper()} at ({actual_lat}°, {actual_lon}°)')
    ax.set_xlabel('Time (UTC)')
    ax.set_ylabel(r'TECU ($10^{16}\ \mathrm{el}/\mathrm{m}^2$)')
    ax.set_title(f'Time Series of {variable.upper()} at ({actual_lat}°, {actual_lon}°)')
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Geomagnetic lines (deferred import — only loaded when needed)
# ---------------------------------------------------------------------------

def _plot_geomagnetic_latitude_lines(ax):
    """Overlay geomagnetic latitude lines on an existing Cartopy axes."""
    try:
        import geomag  # deferred: only imported when explicitly requested
    except ImportError:
        raise ImportError(
            "The 'geomag' package is required for geomagnetic latitude lines. "
            "Install it with:  pip install geomag"
        )

    gm   = geomag.GeoMag()
    lons = np.arange(-180, 180, 2)

    for lat in np.arange(-90, 91, 10):
        geomag_lats = np.array([gm.geo2mag(lat, lon)[0] for lon in lons])
        ax.plot(lons, geomag_lats, 'r--', transform=ccrs.PlateCarree(),
                linewidth=0.7, alpha=0.7)


# ---------------------------------------------------------------------------
# Example usage (uncomment to run)
# ---------------------------------------------------------------------------
# ds = read_ionex('path/to/file.ionex')                      # fast – no metadata
# ds = read_ionex('path/to/file.ionex', read_metadata=True)  # with metadata
#
# # Basic maps (epoch auto-detected from DataArray time coordinate)
# fig, ax = plot_tec_map(ds['tec'].isel(time=0))
# fig, ax = plot_rms_map(ds['rms'].isel(time=0))
#
# # With day/night terminator (epoch read automatically from the DataArray)
# fig, ax = plot_tec_map(ds['tec'].isel(time=6), add_terminator=True)
#
# # With terminator + custom styling
# fig, ax = plot_tec_map(
#     ds['tec'].isel(time=6),
#     add_terminator=True,
#     terminator_kw=dict(night_alpha=0.35, line_color='yellow', line_width=2),
# )
#
# # With terminator on a plain numpy array (must supply epoch explicitly)
# from datetime import datetime
# fig, ax = plot_tec_map(
#     ds['tec'].isel(time=0).values,
#     add_terminator=True,
#     terminator_dt=datetime(2024, 3, 20, 12, 0, 0),
# )
#
# # Disable night shading, keep terminator line only
# fig, ax = plot_rms_map(
#     ds['rms'].isel(time=0),
#     add_terminator=True,
#     terminator_kw=dict(show_night_shade=False, line_color='red'),
# )
#
# fig, ax = plot_time_series(ds, lat=20.0, lon=77.0)
# plt.show()
