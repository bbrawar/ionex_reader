import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime
import xarray as xr
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs

'''
This script reads IONEX files as XARRAY Datasets.
email: bbrawar@gmail.com
Limitation: This script doesn't take values Lat-Long from the file.
'''

def read_ionex(filename):
    """
    Read an IONEX file and extract TEC maps, RMS maps, epochs, and metadata.

    Parameters:
    filename (str): Path to the IONEX file.

    Returns:
    xr.Dataset: A dataset containing TEC and RMS maps with associated metadata.
    """
    with open(filename) as f:
        ionex = f.read()
        tecmaps = [parse_map(t) for t in ionex.split('START OF TEC MAP')[1:]]
        rmsmaps = [parse_rms_map(t) for t in ionex.split('START OF RMS MAP')[1:]]
        epochs = [get_epoch(t) for t in ionex.split('START OF TEC MAP')[1:]]
        metadata = get_metadata(ionex)
        return create_xarray(tecmaps, rmsmaps, epochs, metadata)

def parse_map(tecmap, exponent=-1):
    """
    Parse a TEC map from a string and return it as a numpy array.

    Parameters:
    tecmap (str): String containing the TEC map.
    exponent (int): Exponent for scaling the TEC values.

    Returns:
    np.ndarray: Parsed TEC map.
    """
    tecmap = re.split('.*END OF TEC MAP', tecmap)[0]
    return np.stack([np.fromstring(l, sep=' ') for l in re.split('.*LAT/LON1/LON2/DLON/H\\n', tecmap)[1:]]) * 10**exponent

def parse_rms_map(rmsmap, exponent=-1):
    """
    Parse an RMS map from a string and return it as a numpy array.

    Parameters:
    rmsmap (str): String containing the RMS map.
    exponent (int): Exponent for scaling the RMS values.

    Returns:
    np.ndarray: Parsed RMS map.
    """
    rmsmap = re.split('.*END OF RMS MAP', rmsmap)[0]
    return np.stack([np.fromstring(l, sep=' ') for l in re.split('.*LAT/LON1/LON2/DLON/H\\n', rmsmap)[1:]]) * 10**exponent

def get_epoch(tecmap):
    """
    Extract the epoch from a TEC map string.

    Parameters:
    tecmap (str): String containing the TEC map.

    Returns:
    datetime: Datetime object representing the epoch.
    """
    tecmap = re.split('EPOCH OF CURRENT MAP', tecmap)[0]
    tecmap = np.array(tecmap.split(), dtype=int)
    return datetime(*tecmap)

def get_metadata(ionex):
    """
    Extract metadata from the IONEX file.

    Parameters:
    ionex (str): String containing the entire IONEX file.

    Returns:
    dict: Dictionary containing the extracted metadata.
    """
    metadata = {}
    version_match = re.search(r'(\d+\.\d+)\s+IONOSPHERE MAPS\s+GNSS\s+IONEX VERSION / TYPE', ionex)
    if version_match:
        metadata["ionex_version"] = version_match.group(1)

    pgm_match = re.search(r'(.+?)\s+(.+?)\s+(\d{2}-[A-Z]{3}-\d{2} \d{2}:\d{2})\s+PGM / RUN BY / DATE', ionex)
    if pgm_match:
        metadata["program"] = pgm_match.group(1).strip()
        metadata["run_by"] = pgm_match.group(2).strip()
        metadata["date"] = pgm_match.group(3).strip()

    return metadata

def create_xarray(tecmaps, rmsmaps, epochs, metadata):
    """
    Create an xarray Dataset from TEC and RMS maps, epochs, and metadata.

    Parameters:
    tecmaps (list of np.ndarray): List of TEC maps.
    rmsmaps (list of np.ndarray): List of RMS maps.
    epochs (list of datetime): List of epochs.
    metadata (dict): Dictionary containing metadata.

    Returns:
    xr.Dataset: Dataset containing the TEC and RMS maps with associated metadata.
    """
    # Assuming TEC and RMS maps have a uniform grid structure
    n_lat, n_lon = tecmaps[0].shape
    latitudes = np.linspace(87.5, -87.5, n_lat)
    longitudes = np.linspace(-180, 180, n_lon)
    
    tec_data = np.stack(tecmaps)
    rms_data = np.stack(rmsmaps)
    ds = xr.Dataset(
        {
            "tec": (["time", "latitude", "longitude"], tec_data),
            "rms": (["time", "latitude", "longitude"], rms_data)
        },
        coords={
            "time": epochs,
            "latitude": latitudes,
            "longitude": longitudes
        }
    )
    ds.attrs.update(metadata)
    return ds

def plot_tec_map(tecmap):
    """
    Plot a TEC map using Matplotlib and Cartopy.

    Parameters:
    tecmap (np.ndarray): TEC map to be plotted.
    """
    proj = ccrs.PlateCarree()
    f, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj))
    ax.coastlines()
    h = ax.imshow(tecmap, cmap='viridis', vmin=0, vmax=100, extent=(-180, 180, -87.5, 87.5), transform=proj)

    # Add gridlines and labels (only bottom x-axis and left y-axis)
    gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    try:
        plt.title(f'VTEC map ({tecmap.time.values})')
    except:
        plt.title('VTEC map')
        
    divider = make_axes_locatable(ax)
    ax_cb = divider.new_horizontal(size='5%', pad=0.1, axes_class=plt.Axes)
    f.add_axes(ax_cb)
    cb = plt.colorbar(h, cax=ax_cb)
    plt.rc({'text.usetex': True})
    cb.set_label('TECU ($10^{16} \\mathrm{el}/\\mathrm{m}^2$)')

def plot_rms_map(rmsmap):
    """
    Plot an RMS map using Matplotlib and Cartopy.

    Parameters:
    rmsmap (np.ndarray): RMS map to be plotted.
    """
    proj = ccrs.PlateCarree()
    f, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj))
    ax.coastlines()
    h = ax.imshow(rmsmap, cmap='viridis', vmin=0, vmax=10, extent=(-180, 180, -87.5, 87.5), transform=proj)

    # Add gridlines and labels (only bottom x-axis and left y-axis)
    gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    try:
        plt.title(f'RMS map ({rmsmap.time.values})')
    except:
        plt.title('RMS map')
        
    divider = make_axes_locatable(ax)
    ax_cb = divider.new_horizontal(size='5%', pad=0.1, axes_class=plt.Axes)
    f.add_axes(ax_cb)
    cb = plt.colorbar(h, cax=ax_cb)
    plt.rc({'text.usetex': True})
    cb.set_label('TECU ($10^{16} \\mathrm{el}/\\mathrm{m}^2$)')

# Example usage:
# ds = read_ionex('path_to_your_file.ionex')
# tecmap = ds['tec'].isel(time=0).values  # Plot the first time slice of the TEC map
# plot_tec_map(tecmap)
# rmsmap = ds['rms'].isel(time=0).values  # Plot the first time slice of the RMS map
# plot_rms_map(rmsmap)
# plt.show()
