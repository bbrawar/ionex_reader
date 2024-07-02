import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime
import xarray as xr
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs

def get_tecmaps(filename):
    with open(filename) as f:
        ionex = f.read()
        tecmaps = [parse_map(t) for t in ionex.split('START OF TEC MAP')[1:]]
        epochs = [get_epoch(t) for t in ionex.split('START OF TEC MAP')[1:]]
        return create_xarray(tecmaps, epochs)

def parse_map(tecmap, exponent=-1):
    tecmap = re.split('.*END OF TEC MAP', tecmap)[0]
    return np.stack([np.fromstring(l, sep=' ') for l in re.split('.*LAT/LON1/LON2/DLON/H\\n', tecmap)[1:]]) * 10**exponent

def get_epoch(tecmap):
    tecmap = re.split('EPOCH OF CURRENT MAP', tecmap)[0]
    tecmap = np.array(tecmap.split(), dtype=int)
    return datetime(*tecmap)
    
def create_xarray(tecmaps, epochs):
    n_lat, n_lon = tecmaps[0].shape
    latitudes = np.linspace(87.5, -87.5, n_lat)
    longitudes = np.linspace(-180, 180, n_lon)
    
    data = np.stack(tecmaps)
    ds = xr.Dataset(
        {
            "tec": (["time", "latitude", "longitude"], data)
        },
        coords={
            "time": epochs,
            "latitude": latitudes,
            "longitude": longitudes
        }
    )
    return ds

def get_tec(tecmap, lat, lon):
    i = round((87.5 - lat) * (tecmap.shape[0] - 1) / (2 * 87.5))
    j = round((180 + lon) * (tecmap.shape[1] - 1) / 360)
    return tecmap[i, j]

def plot_tec_map(tecmap):
    proj = ccrs.PlateCarree()
    f, ax = plt.subplots(1, 1, subplot_kw=dict(projection=proj))
    ax.coastlines()
    h = plt.imshow(tecmap, cmap='viridis', vmin=0, vmax=100, extent=(-180, 180, -87.5, 87.5), transform=proj)
    try:
        plt.title(f'VTEC map({tecmap.time.values})')
    except AttributeError:
        plt.title('VTEC map')
    divider = make_axes_locatable(ax)
    ax_cb = divider.new_horizontal(size='5%', pad=0.1, axes_class=plt.Axes)
    f.add_axes(ax_cb)
    cb = plt.colorbar(h, cax=ax_cb)
    plt.rc({'text.usetex': True})
    cb.set_label('TECU ($10^{16} \\mathrm{el}/\\mathrm{m}^2$)')
