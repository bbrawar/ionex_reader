# import unittest
# from ionex_reader.ionex import get_tecmaps, create_xarray

# class TestIonexReader(unittest.TestCase):

#     def test_create_xarray(self):
#         tecmaps = [np.random.rand(180, 360) for _ in range(5)]
#         epochs = [datetime(2020, 1, 1) for _ in range(5)]
#         ds = create_xarray(tecmaps, epochs)
#         self.assertEqual(ds.dims['time'], 5)
#         self.assertEqual(ds.dims['latitude'], 180)
#         self.assertEqual(ds.dims['longitude'], 360)

# if __name__ == '__main__':
#     unittest.main()

import unittest
import numpy as np
from datetime import datetime
from ionex_reader.ionex import create_xarray

class TestIonexReader(unittest.TestCase):

    def test_create_xarray(self):
        # Create mock data for tecmaps
        tecmaps = [np.random.rand(180, 360) for _ in range(5)]
        epochs = [datetime(2020, 1, 1, hour=i) for i in range(5)]  # Create 5 hourly epochs

        # Call create_xarray to test
        ds = create_xarray(tecmaps, None, epochs)  # Provide None for rmsmaps if testing only tecmaps

        # Assert dataset dimensions
        self.assertEqual(ds.dims['time'], 5, "Time dimension should have 5 values")
        self.assertEqual(ds.dims['latitude'], 180, "Latitude dimension should have 180 values")
        self.assertEqual(ds.dims['longitude'], 360, "Longitude dimension should have 360 values")

        # Assert dataset contains expected variables
        self.assertIn('tec', ds.data_vars, "Dataset should contain 'tec' variable")

        # Assert latitude and longitude values are as expected
        np.testing.assert_almost_equal(ds['latitude'].values[0], 87.5, decimal=1)
        np.testing.assert_almost_equal(ds['latitude'].values[-1], -87.5, decimal=1)
        np.testing.assert_almost_equal(ds['longitude'].values[0], -180.0, decimal=1)
        np.testing.assert_almost_equal(ds['longitude'].values[-1], 180.0, decimal=1)

if __name__ == '__main__':
    unittest.main()
