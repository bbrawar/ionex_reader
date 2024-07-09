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
from ionex_reader.ionex import read_ionex, plot_tec_map, plot_time_sereies

# Read TEC maps from an IONEX file
ds = read_ionex('path_to_your_file.ionex')
print(ds)  # Print the xarray Dataset

# Plot the first TEC map
plot_tec_map(ds.tec.isel(time=0))
plt.show()

# Plot the time series for a specific latitude and longitude
plot_time_series(ds, lat=45.0, lon=90.0, variable='tec')
plt.show()
```

## Functions
1. `read_ionex(filename)`: Reads an IONEX file and returns an xarray Dataset with TEC maps.
2. `plot_tec_map(tecmap)`: Plots a TEC map using Matplotlib and Cartopy.
3. `plot_rms_map(rmsmap)`: Plots a TEC map using Matplotlib and Cartopy.
4. `plot_time_series(ds,lat,lon,variable='tec')`: Plots a time series plot of tec values at any lat-long.
## Dependencies
`numpy, matplotlib, xarray, cartopy`


## Author
[Bhuvnesh Brawar](bbrawar.github.io)</br>
[bbrawar@gmail.com](mailto:bbrawar@gmail.com)</br>
[phd2101121005@iiti.ac.in](mailto:phd2101121005@iiti.ac.in)

