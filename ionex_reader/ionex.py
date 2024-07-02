import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime
import xarray as xr
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs

'''
This reads IONEX files as XARRAY Datasets.
email: bbrawar@gmail.com
Limitation: This script doesn't take values Lat-Long from the file.
'''

def read_ionex(filename):
    with open(filename) as f:
        ionex = f.read()
        tecmaps = [parse_map(t) for t in ionex.split('START OF TEC MAP')[1:]]
        rmsmaps = [parse_rms_map(t) for t in ionex.split('START OF RMS MAP')[1:]]
        epochs = [get_epoch(t) for t in ionex.split('START OF TEC MAP')[1:]]
        return create_xarray(tecmaps, rmsmaps, epochs)

def parse_map(tecmap, exponent=-1):
    tecmap = re.split('.*END OF TEC MAP', tecmap)[0]
    return np.stack([np.fromstring(l, sep=' ') for l in re.split('.*LAT/LON1/LON2/DLON/H\\n', tecmap)[1:]]) * 10**exponent

def parse_rms_map(rmsmap, exponent=-1):
    rmsmap = re.split('.*END OF RMS MAP', rmsmap)[0]
    return np.stack([np.fromstring(l, sep=' ') for l in re.split('.*LAT/LON1/LON2/DLON/H\\n', rmsmap)[1:]]) * 10**exponent

def get_epoch(tecmap):
    tecmap = re.split('EPOCH OF CURRENT MAP', tecmap)[0]
    tecmap = np.array(tecmap.split(), dtype=int)
    return datetime(*tecmap)

def create_xarray(tecmaps, rmsmaps, epochs):
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
    return ds

def plot_tec_map(tecmap):
    proj = ccrs.PlateCarree()
    f, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj))
    ax.coastlines()
    h = ax.imshow(tecmap, cmap='viridis', vmin=0, vmax=100, extent=(-180, 180, -87.5, 87.5), transform=proj)

    # Add gridlines and labels
    ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
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
    proj = ccrs.PlateCarree()
    f, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj))
    ax.coastlines()
    h = ax.imshow(rmsmap, cmap='viridis', vmin=0, vmax=10, extent=(-180, 180, -87.5, 87.5), transform=proj)

    # Add gridlines and labels
    ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    try:
        plt.title(f'rms map ({tecmap.time.values})')
    except:
        plt.title('rms map')
        
    divider = make_axes_locatable(ax)
    ax_cb = divider.new_horizontal(size='5%', pad=0.1, axes_class=plt.Axes)
    f.add_axes(ax_cb)
    cb = plt.colorbar(h, cax=ax_cb)
    plt.rc({'text.usetex': True})
    cb.set_label('TECU ($10^{16} \\mathrm{el}/\\mathrm{m}^2$)')

