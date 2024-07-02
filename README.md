# ionex_reader

A Python module to read and plot IONEX TEC maps as xarray Datasets.

## Installation

Clone the repository and install the package using `pip`:

### bash
```
git clone https://github.com/bbrawar/ionex_reader.git
cd ionex_reader
pip install .
```
## Usage 
```
from ionex_reader.ionex import get_tecmaps, plot_tec_map

# Read TEC maps from an IONEX file
ds = get_tecmaps('path_to_your_file.ionex')
print(ds)  # Print the xarray Dataset

# Plot the first TEC map
plot_tec_map(ds.tec.isel(time=0))
plt.show()
```

## Functions
1. `get_tecmaps(filename)`: Reads an IONEX file and returns an xarray Dataset with TEC maps.
2. `plot_tec_map(tecmap)`: Plots a TEC map using Matplotlib and Cartopy.

## Dependencies
`numpy, matplotlib, xarray, cartopy`
